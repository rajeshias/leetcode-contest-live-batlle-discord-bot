import pickle
import time
import discord
from datetime import datetime
from discord.ext import tasks
import json
import requests
from texttable import Texttable

TOKEN = ''
if not TOKEN:
    exit()

client = discord.Client()

today = datetime.today().strftime('%Y-%m-%d')
day = datetime.today().strftime('%A')
count = 0
no = 1
x = 'bw'

@tasks.loop(seconds=15.0)
async def live(this):
    ball = {
        'Accepted': '🟢',
        'Time Limit Exceeded': '🟡',
        'Wrong Answer': '🔴',
        'Runtime Error': '🟠',
        'Output Limit Exceeded': '🟤',
        'Compile Error': '🔵'
    }
    data = load_obj(f'{x}-{no}')
    num = data['id'].split('-')[-1]
    name = 'biweekly' if data['id'].split('-')[0] == 'bw' else 'weekly'
    adjust = 72000 if data['id'].split('-')[0] == 'bw' else 28800
    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.set_max_width(108)
    items = [["Name"] + data['q']]
    totalscore = {}
    for user in data['users']:
        each = []
        sub = sorted(getsubmissions(user), key=lambda d: d['timestamp'])
        lang = ''
        total = 0
        for q in data['q']:
            cells = ''
            cellItem = [i for i in sub if i['title'] == q]
            for cell, score in zip(cellItem, data['score']):
                cells += ball[cell['statusDisplay']]
                if cell['statusDisplay'] == 'Accepted':
                    total += score
                    t = time.strftime('%H:%M:%S', time.localtime(int(cell['timestamp']) - adjust))
                    cells += f' ({t})'
                lang = f" ({cell['lang']})"
            each.append(cells)
        totalscore[user] = total
        items.append([user + lang] + each)
    table.add_rows(items)
    nl = '\n'
    await this.edit(content=f'{name} contest **#{num}** (*use /stop to live broadcast*)\n' + '```\n' + table.draw() +
                            f'```\n**Scoreboard live**:\n:medal:{nl.join([f"{i} - {j}" for i, j in sorted(totalscore.items(),key=lambda item: item[1], reverse=True)])}')


def getsubmissions(user):
    headers = {
        'authority': 'leetcode.com',
        'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'content-type': 'application/json',
        'accept': '*/*',
        'sec-ch-ua-platform': '"Windows"',
        'origin': 'https://leetcode.com',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-language': 'en-US,en;q=0.9',
    }

    data = '{"operationName":"getRecentSubmissionList","variables":{"username":' + f'"{user}"' + '},"query":"query getRecentSubmissionList($username: String!, $limit: Int) {\\n  recentSubmissionList(username: $username, limit: $limit) {\\n    title\\n    titleSlug\\n    timestamp\\n    statusDisplay\\n    lang\\n  }\\n  languageList {\\n    id\\n    name\\n    verboseName\\n }\\n}\\n"}'

    response = requests.post('https://leetcode.com/graphql', headers=headers, data=data)
    result = json.loads(response.content)['data']['recentSubmissionList']
    tempData = load_obj(f'{x}-{no}')
    return [i for i in result if i['title'] in tempData['q']]


def getcontest(num, x):
    y = 'bi' if x == 'bw' else ''
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
    }
    response = requests.get(f'https://leetcode.com/contest/api/info/{y}weekly-contest-{num}/', headers=headers)
    return json.loads(response.content)['questions']


def create_obj(obj, name):
    with open(name + '.pkl', 'a+b') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)


@client.event
async def on_ready():
    print('ready to go')


@client.event
async def on_message(message):
    global day
    global today
    global no
    global x
    global count

    if message.content.startswith('/stop'):
        live.cancel()
        await message.channel.send('Stopped...')


    if message.author.bot:
        return
    elif live.is_running():
        count += 1
        if count > 8:
            live.cancel()
            this = await message.channel.send('```Parkour... ```')
            live.start(this)
            count = 0


    if message.content.startswith('/help'):
        await message.channel.send(
            '```/leet {num}   - load biweekly contest\n/leet w {num} - load weekly contest\n/add          - add users '
            'participating\n/clear        - clear users participating\n/start        - play the '
            'contest\n-----------------------------------------------\n```**color ref:**\n:green_circle: - Accepted\n'
            ':yellow_circle: - Time Limit Exceeded\n:blue_circle: - Compile Error\n:brown_circle: - Output Limit Exceeded\n'
            ':orange_circle: - Runtime Error\n:red_circle: - Wrong Answer')


    if message.content.startswith('/leet'):
        x = 'bw' if 'w' not in message.content else 'w'
        if message.content.split(' ')[-1].strip().isnumeric():
            no = int(message.content.split(' ')[-1].strip())
        else:
            await message.channel.send('expecting number after /leet')

        try:
            questions = [q['title'] for q in getcontest(no, x)]
            score = [q['credit'] for q in getcontest(no, x)]
            await message.channel.send('Switched Contest')
            data = load_obj(f'{x}-{no}')
            data['q'] = questions
            data['score'] = score
            save_obj(data, f'{x}-{no}')
            if not data['users']:
                await message.channel.send('No participants yet. Please add users by using /add')
            else:
                print(data['users'])

        except FileNotFoundError:
            create_obj({'id': f'{x}-{no}', 'users': set(), 'q': [], 'score': []}, f'{x}-{no}')
            questions = [q['title'] for q in getcontest(no, x)]
            score = [q['credit'] for q in getcontest(no, x)]
            data = load_obj(f'{x}-{no}')
            data['q'] = questions
            data['score'] = score
            save_obj(data, f'{x}-{no}')
            await message.channel.send('No participants yet. Please add users by using /add')
            return


    if message.content.startswith('/add'):
        user = message.content.split('/add')[-1].strip().lower()
        try:
            data = load_obj(f'{x}-{no}')
        except FileNotFoundError:
            await message.channel.send('No Contest started. Use /leet {num}')
            return
        if not data['q']:
            await message.channel.send('No Contest started. Use /leet {num}')
            return
        if user not in data['users']:
            data['users'].add(user)
        else:
            await message.channel.send('user already exists')
            return
        save_obj(data, f'{x}-{no}')
        await message.channel.send('users participating right now (/clear to reset):\n')
        await message.channel.send('\n'.join([i for i in data['users']]))

    if message.content.startswith('/clear'):
        data = load_obj(f'{x}-{no}')
        data['users'] = set()
        save_obj(data, f'{x}-{no}')
        await message.channel.send('*flushing sound*')

    if message.content.startswith('/start'):
        if live.is_running():
            await message.channel.send('``` please use /stop to quit the current contest... ```')
            return
        try:
            data = load_obj(f'{x}-{no}')
        except FileNotFoundError:
            await message.channel.send('No Contest started. Use /leet {num}')
            return
        if not data['users']:
            await message.channel.send('``` add users first... ```')
            return
        this = await message.channel.send('``` Loading... ```')
        live.start(this)


client.run(TOKEN)
