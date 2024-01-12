
async def status_task():
    await bot.wait_until_ready()

    while not bot.is_closed():
        online_members = {member for guild in bot.guilds for member in guild.members if not member.bot and member.status != discord.Status.offline}

        play = ["with the \"help\" command", " ", "with your mind", "ƃuᴉʎɐlԀ", "...something?",
                "a game? Or am I?", "¯\_(ツ)_/¯", f"with {len(online_members)} people", "with the Simple Machine"]
        listen = ["smart music", "... wait I can't hear anything"]
        watch = ["TV", "YouTube vids", "over you",
                 "how to make a bot", "C tutorials", "sm213 execute", "I, Robot"]

        rng = random.randrange(0, 3)

        if rng == 0:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=random.choice(play)))
        elif rng == 1:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random.choice(listen)))
        else:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(watch)))

        await asyncio.sleep(30)


async def wipe_dms():
    guild = bot.get_guild(int(os.getenv("SERVER_ID")))
    while True:
        await asyncio.sleep(300)
        bot.get_cog("SM213").queue = list(filter(lambda x: time.time() - x[1] < 300, bot.get_cog("SM213").queue))
        now = datetime.utcnow()
        for channel in filter(lambda c: c.name.startswith("213dm-"), guild.channels):
            async for msg in channel.history(limit=1):
                if (now - msg.created_at).total_seconds() >= 86400:
                    await next(i for i in guild.roles if i.name == channel.name).delete()
                    await channel.delete()
                    break
            else:
                await next(i for i in guild.roles if i.name == channel.name).delete()
                await channel.delete()

def get_local_assessments():
    names = []
    for header in bot.pl_dict:
        for entry in bot.pl_dict[header]:
            names.append(f"{entry['label']} {entry['name']}")
    return names


async def crawl_prairielearn():
    channel = bot.get_channel(int(os.getenv("NOTIF_CHANNEL")))
    while True:
        try: 
            new_pl_dict = defaultdict(list)
            total_assignments = get_pl_data("get_assessments", {"course_instance_id": int(os.getenv("COURSE_ID"))})
            for assignment in total_assignments:
                assessment_id = assignment["assessment_id"]
                schedule_data = get_pl_data("get_assessment_access_rules", {"course_instance_id": int(os.getenv("COURSE_ID")), "assessment_id": assessment_id})
                modes = []
                not_started = False
                for mode in schedule_data:
                    if mode["uids"] != None: continue
                    if mode["start_date"]:
                        offset = int(mode["start_date"][-1])
                    else:
                        offset = 0

                    if mode["start_date"] and mode["credit"] == 100:
                        start = time.mktime(time.strptime("-".join(mode["start_date"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S"))
                        now = time.time() - offset * 60
                        if start > now: 
                            not_started = True
                            break
                    
                    if not mode["end_date"]: 
                        end = None
                        end_unix = 0
                    else: 
                        end_unix = time.strptime("-".join(mode["end_date"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S")
                        end = time.strftime("%H:%M PST, %a, %b, %d", end_unix)
                        end_unix = time.mktime(end_unix)

                    modes.append({
                        "credit": mode["credit"],
                        "end":    end,
                        "end_unix": end_unix,
                        "offset": offset
                    })

                if not_started:
                    continue

                fielddata = {
                    "id": assessment_id,
                    "color": assignment["assessment_set_color"], 
                    "label": assignment["assessment_label"],
                    "name":  assignment["title"],
                    "modes": modes
                }
                new_pl_dict[assignment["assessment_set_heading"]].append(fielddata)

            seen_assessments = get_local_assessments()
            sent = False
            for header in new_pl_dict:
                for entry in new_pl_dict[header]:
                    if entry not in bot.pl_dict[header]:
                        sent = True
                        if f"{entry['label']} {entry['name']}" not in seen_assessments:
                            title = f"New {['Assignment', 'Quiz'][entry['label'].startswith('Q')]}"
                        else:
                            title = f"{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} {entry['label']} Updated,"
                        for mode in entry["modes"]:
                            if mode["credit"] == 100 and mode["end"]:
                                title += f" Due at {mode['end']}"
                                break
                        else:
                            title += f" (No Due Date)"

                        embed = discord.Embed(color = int("%x%x%x" % colormap[entry["color"]], 16), title = title, description = f"[**{entry['label']} {entry['name']}**](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)")
                        embed.set_footer(text = "CPSC 213 on PrairieLearn")
                        embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                        # await channel.send(embed = embed)

                    for mode in entry["modes"]:
                        if mode["credit"] == 100 and mode["end"] and (mode["end_unix"] + 60*mode["offset"]) - time.time() < 86400 and entry["label"] + " " + entry["name"] not in bot.due_tomorrow:
                            # bot.due_tomorrow.append(entry["label"]+" "+entry["name"])
                            hourcount = round(((mode["end_unix"] + 60*mode["offset"]) - time.time())/3600, 2)
                            if hourcount < 0: continue
                            embed = discord.Embed(color = int("%x%x%x" % colormap[entry["color"]], 16), title = f"{['Assignment', 'Quiz'][entry['label'].startswith('Q')]} {entry['label']} Due in < {hourcount} Hours\n({mode['end']})", description = f"[**{entry['label']} {entry['name']}**](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)")
                            embed.set_footer(text = "CPSC 213 on PrairieLearn")
                            embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
                            # await channel.send(embed = embed)
                            sent = True
                            break

            #if sent:
                #await channel.send(f"<@&{os.getenv('NOTIF_ROLE')}>")

            bot.pl_dict = new_pl_dict
            writeJSON(dict(bot.pl_dict), "data/pl.json")
            writeJSON(bot.due_tomorrow, "data/tomorrow.json")
            thetime = datetime.utcfromtimestamp(time.time() - (7 * 60 * 60)).strftime('%Y-%m-%d %H:%M:%S')
            embed = discord.Embed(title = f"Current Assessments on CPSC 213 PrairieLearn", description = f"Updates every 30 minutes, last checked {thetime}", color = 0x8effc1)
            thechannel = bot.get_channel(884874356654735413)
            for assigntype in bot.pl_dict:
                entrylist = bot.pl_dict[assigntype]
                formattedentries = []
                seenmodes = []
                for entry in entrylist:
                    skip = False
                    formatted = f"`{entry['label']}` **[{entry['name']}](https://ca.prairielearn.com/pl/course_instance/{os.getenv('COURSE_ID')}/assessment/{entry['id']}/)**\nCredit:\n"
                    for mode in entry["modes"]:
                        if mode['end'] and mode['credit'] == 100:
                            offset = int(mode["end"][-1])
                            now = time.time() - offset * 60
                            if mode['end_unix'] < now:
                                skip = True
                                break

                        fmt = f"· {mode['credit']}% until {mode['end']}\n"
                        if fmt not in seenmodes:
                            formatted += fmt
                            seenmodes.append(fmt)

                    if skip: continue

                    formattedentries.append(formatted)
                embed.add_field(name = f"\u200b\n***{assigntype.upper()}***", value = "\n".join(formattedentries) + '\u200b', inline = False)
            
            embed.set_thumbnail(url = "https://cdn.discordapp.com/attachments/511797229913243649/803491233925169152/unknown.png")
            # msg = await thechannel.fetch_message(886048835183460384)
            # await msg.edit(embed = embed)
            await asyncio.sleep(1800)
        except Exception as error:
            await channel.send(str(error))
            etype = type(error)
            trace = error.__traceback__
            print(("".join(traceback.format_exception(etype, error, trace, 999))).replace("home/rq2/.local/lib/python3.9/site-packages/", ""))
            await asyncio.sleep(60)


def get_pl_data(method, options):
    # based on https://github.com/PrairieLearn/PrairieLearn/blob/master/tools/api_download.py
    
    start_time = time.time()
    retry_502_max = 30
    retry_502_i = 0
    while True:
        r = getattr(bot.pl, method)(options)
        if r.status_code == 200:
            break
        elif r.status_code == 502:
            retry_502_i += 1
            if retry_502_i >= retry_502_max:
                raise Exception(f'Maximum number of retries reached on 502 Bad Gateway Error')
            else:
                time.sleep(10)
                continue
        else:
            raise Exception(f'Invalid status returned: {r.status_code}')

    data = r.json()
    return data
