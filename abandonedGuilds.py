#!/usr/bin/env python

import sys, getopt, requests,pymustache
from datetime import *
from dateutil.parser import *
from dateutil.relativedelta import *
from unidecode import unidecode
try:
    from tqdm import tqdm
except:
    def tqdm(*args, **kwargs):
        if args:
            return args[0]
        return kwargs.get('iterable', None)

# Constants
API_BASE = 'https://habitica.com/api/v3/'
DEFAULT_TEMPLATE = 'wikia.template'
ABANDONED_LEADER = 6

AUTH = {}

def usage():
    print('''
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
'''.format(sys.argv[0], DEFAULT_TEMPLATE))

def get(path, params={}):
    r = requests.get(API_BASE + path, params=params, headers=AUTH).json()
    if r['success']:
        return r['data']
    else:
        print API_BASE + path
        print params
        raise Exception('{0[error]}: {0[message]}'.format(r))

def formatDate(dateString):
    parsedDate = parse(dateString, ignoretz=True)
    splitDate = {
        'year': parsedDate.year,
        'month': parsedDate.month,
        'day': parsedDate.day,
    }
    return '{{{{displaydate|{0[day]}|{0[month]}|{0[year]}}}}}'.format(splitDate)

def main():
    personal = False
    useTemplate = False
    limit = 0
    output = ''
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'htl:o:', ['help', 'uid=', 'token=', 'template', 'personal', 'limit=', 'output='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        elif o == '--uid':
            AUTH['x-api-user'] = a
        elif o == '--token':
            AUTH['x-api-key'] = a
        elif o in ('-t', '--template'):
            useTemplate = True
            templateFile = a if a != '' else DEFAULT_TEMPLATE
        elif o == '--personal':
            personal = True
        elif o in ('-l', '--limit'):
            limit = int(a)
        elif o in ('-o', '--output'):
            output = a
    
    if (output != '') and not useTemplate:
        print 'Use -o with --t'
        usage()
        sys.exit(2)
    
    # Authentication
    if (not ('x-api-user' in AUTH)) and 'x-api-key' in AUTH:
        print 'Use both --uid and --token, or just --uid'
        usage()
        sys.exit(2)
    elif not ('x-api-user' in AUTH and 'x-api-key' in AUTH):
        print 'Authentication'
        if not 'x-api-user' in AUTH:
            AUTH['x-api-user'] = raw_input('User ID: ')
        AUTH['x-api-key'] = raw_input('API Token: ')

    # Get group IDs
    allGroups = get('groups', {'type': 'guilds' if personal else 'publicGuilds'})
    
    groups = allGroups[:]
    
    if limit > 0:
        groups = allGroups[:limit]
    elif limit < 0:
        groups = allGroups[limit:]
    
    # Set up progress bar
    groupsBar = tqdm(groups, unit="guilds")

    # Loop through each group, and append guilds who have leaders that have been logged out for over ABANDONED_LEADER months
    abandonedGuilds = []
    for group in groupsBar:
        # Get leader data
        leaderId = group['leader']
        # Reject short uids
        if(len(leaderId) == 36):
            leader = get('members/' + leaderId)
            
            # Find how long ago
            leaderLoginDate = parse(leader['auth']['timestamps']['loggedin'], ignoretz=True)
            timeDifference = relativedelta(date.today(), leaderLoginDate)
            years = (0 if timeDifference.years is None else timeDifference.years)
            months = (0 if timeDifference.months is None else timeDifference.months) + 12 * years
            
            if months >= ABANDONED_LEADER:
                # Guild is possibly abandoned by leader, record guild
                group = get('groups/'+group['_id'])
                abandonedGuilds.append({
                    'guild': group,
                    'leader': leader,
                    'abandoned': timeDifference
                })
    # Sort by name, then reverse months
    abandonedGuilds_sorted = sorted(sorted(abandonedGuilds, key=lambda guild: guild['guild']['name']), key=lambda guild: guild['abandoned'].years*12 + guild['abandoned'].months, reverse=True)
    
    if not useTemplate:
        for abandonedGuild in abandonedGuilds_sorted:
            print u'{}: {} - {}'.format(abandonedGuild['guild']['name'], abandonedGuild['leader']['profile']['name'], abandonedGuild['abandoned'].years*12 + abandonedGuild['abandoned'].months)
    else:
        guilds = []
        for guild in abandonedGuilds_sorted:
            guild['guild']['name'] = lambda name: unidecode(name)
            guild['guild']['decription'] = lambda name: unidecode(name)
            guild['guild']['leaderMessage'] = lambda name: unidecode(name)
            guild['leader']['profile']['name'] = lambda name: unidecode(name)
            guild['guild']['leaderInfo'] = guild['leader']
            guilds.append(guild['guild'])
        data = {
            'guilds': guilds,
            'today': date.today().isoformat()
        }
        with open(templateFile, 'r') as t:
            compiledTemplate = pymustache.compiled(t.read())
            compiledTemplate.filters['date'] = formatDate
            outputData = compiledTemplate.render(data)
        
        if output != '':
            with open(output, 'w+') as outputFile:
                outputFile.write(outputData)
        else:
            print outputData
    

if __name__ == '__main__':
    main()