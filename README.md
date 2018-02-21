    usage: python {} [options]
    -h, --help
        See this message
    --uid uid
        User ID for authentication
    --token key
        API token for authentication. If used, must be with --uid
    --personal
        Flag to indicate searching through user's joined guilds (useful if searching for a guild to help)
    -t [file], --template [file]
        Path to pymustache file for formatting. If not specified, prints in the format of
        {{Guild Name}}: {{Guild Leader}} - {{Months logged out}}
        If file is not specified, defaults to {}
    -o file, --output file
        File to output to. Only used with -t or --template
    -l num, --limit num
        Limit the guilds
        if num is 0: all the guilds
        if num is positive: limit to the top num guilds (by size)
        if num is negative: limit to the bottom num guilds (by size)
