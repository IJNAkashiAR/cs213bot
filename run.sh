#!/bin/sh

usage() {
    echo "Usage: $0 [-h] [-r] [-i] [-d]"
    echo "  -h  Display this help message"
    echo "  -r  Run the cs213 Docker image"
    echo "  -d  Delete the cs213 Docker image"
    echo "  -i  Build cs213 Docker image"
    exit 1
}

init() {
    docker volume create cs213bot-volume
    docker build --tag=cs213bot .
    echo "Docker image built. Now run this script again with the -r argument to start the bot"
}

remove() {
    echo "Remove done"
    exit 0
}

run() {
    docker run --rm \
           --volume cs213bot-volume:/data\
           cs213bot:latest
}

while getopts ":hird" opt; do
    case ${opt} in
        h )
            usage
            ;;
        i )
            echo "Building Docker image"
            init
            ;;
        r )
            echo "Running cs213bot"
            run
            ;;
        d )
            echo "Deleting cs213bot"
            delete
            ;;
        \?)
            echo "Invalid Option: -$OPTARG requires an argument" 1>&2
            usage
            ;;
    esac
done

if [ $# == 0 ]; then
    usage
fi
