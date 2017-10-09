#!/usr/bin/env python

import sys, argparse, requests, pymustache, json
from datetime import *
from dateutil.parser import *
from dateutil.relativedelta import *
from time import *
from unidecode import unidecode
from time import sleep
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

def get(path, params={}, tried=0):
    r = requests.get(API_BASE + path, params=params, headers=AUTH)
    
    if r.status_code == 200:
        return r.json()['data']
    elif r.status_code == 500:
        # A server error occured, wait 5 seconds and try again unless it has been tried more than 5 times
        if tried >= 5:
            raise Exception('Failed too many times')
        print 'Error code 500 encountered, waiting 5 seconds'
        sleep(5)
        tried += 1
        return get(path, params, tried).json['data']
    else:
        print API_BASE + path
        print params
        raise Exception('{0[error]}: {0[message]}'.format(r.json()))
        

def formatDate(dateString):
    if dateString != 'N/A':
        try:
            parsedDate = parse(dateString, ignoretz=True)
            splitDate = {
                'year': parsedDate.year,
                'month': parsedDate.month,
                'day': parsedDate.day,
            }
        except:
            try:
                parsedDate = gmtime(int(dateString)/1000)
                splitDate = {
                    'year': parsedDate.tm_year,
                    'month': parsedDate.tm_mon,
                    'day': parsedDate.tm_mday,
                }
            except:
                tqdm.write('Error! {0}'.format(sys.exc_info()[0]))
        formattedDate = '{{{{displaydate|{0[year]}|{0[month]}|{0[day]}}}}}'.format(splitDate)
        return formattedDate
    else:
        return 'N/A'

def main():
    argparser = argparse.ArgumentParser(description='Search for abandoned Guilds')
    argparser.add_argument('uid', help='User ID')
    argparser.add_argument('token', help='API Token')
    argparser.add_argument('-o', '--output', help='file name to output to')
    argparser.add_argument('-t', '--template', help='Pymustache template to use as processing', default=DEFAULT_TEMPLATE)
    argparser.add_argument('--personal', action='store_true', help='search through joined Guilds')
    args = argparser.parse_args()
    
    AUTH['x-api-user'] = args.uid
    AUTH['x-api-key'] = args.token

    # Get group IDs
    allGroups = get('groups', {'type': 'guilds' if args.personal else 'publicGuilds'})
    
    # Set up progress bar
    groupsBar = tqdm(allGroups, unit='guilds')

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
    # Sort by id
    abandonedGuilds_sorted = sorted(abandonedGuilds, key=lambda guild: guild['guild']['_id'])
    
    if not args.template:
        for abandonedGuild in abandonedGuilds_sorted:
            print u'{}: {} - {}'.format(abandonedGuild['guild']['name'], abandonedGuild['leader']['profile']['name'], abandonedGuild['abandoned'].years*12 + abandonedGuild['abandoned'].months)
    else:
        guilds = []
        
        # Deal with Unicode
        transilerate = lambda string: unidecode(string) if type(string) is unicode else string
        for guild in abandonedGuilds_sorted:
            guild['guild']['name'] = transilerate(guild['guild']['name'])
            guild['guild']['description'] = transilerate(guild['guild'].setdefault('description', 'N/A'))
            guild['guild']['summary'] = transilerate(guild['guild'].setdefault('summary', 'N/A'))
            guild['leader']['profile']['name'] = transilerate(guild['leader']['profile']['name'])
            guild['guild']['leaderInfo'] = guild['leader']
            # Chat
            guild['guild']['chat'] = {
                '1st': str(guild['guild']['chat'][0]['timestamp']) if len(guild['guild']['chat']) >= 1 else 'N/A',
                '5th': str(guild['guild']['chat'][4]['timestamp']) if len(guild['guild']['chat']) >= 5 else 'N/A',
                '20th': str(guild['guild']['chat'][19]['timestamp']) if len(guild['guild']['chat']) >= 20 else 'N/A',
            }
            guilds.append(guild['guild'])
        
        # Get data ready
        data = {
            'guilds': guilds,
            'today': date.today().isoformat()
        }
        with open(args.template, 'r') as t:
            compiledTemplate = pymustache.compiled(t.read())
            compiledTemplate.filters['date'] = lambda date: formatDate(date)
            outputData = compiledTemplate.render(data)
        
        if args.output != '':
            with open(args.output, 'w+') as outputFile:
                outputFile.write(outputData)
        else:
            print outputData
    

if __name__ == '__main__':
    main()