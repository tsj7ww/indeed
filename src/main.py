# standard
import json
import os
import io
import sys
import datetime
import logging
import concurrent.futures

# etc
import time
import random
import re
import uuid

# aws
import boto3

# web scrape - imported in layer
import requests
import bs4

def CONFIG(env):
    """"""
    if env=='dev':
        None
    elif env=='qa':
        None
    elif env=='prod':
        None
    else:
        raise Exception('Unknown environment.')

    cwd = os.getcwd()
    now = datetime.datetime.now()
    dt = '%Y%m%d'
    dttm = '%Y%m%d_%H%M%S'

    eid = 'tsj7ww'
    proc = 'Indeed'
    pid = 'etl-indeed'

    region = 'us-east-1'
    rgn = region.replace('-','')

    cfg = {
        'now': now,
        'cwd': cwd,
        'pid': pid,
        'proc': proc,
        'region': region,
        'eid': eid,
        'arn': '{arn}:{partition}:{service}:{region}:{account-id}:{resource-id}',
        'indeed': {
            'url': 'https://www.indeed.com/jobs?start={NUM}&q={QRY}&l={LOC}',
            'replace': {' ':'%20',',':'%2C'}
        },
        'db': {
            'url': 'https://dynamodb.{}.amazonaws.com'.format(region),
            'table': pid
        },
        'email': {
            'Source': os.environ['SENDER'],
            'Destination': {'ToAddresses': os.environ['STAKEHOLDERS'].split(',')},
            'Message': {
                'Subject': {'Data': 'Indeed Weekly Summary','Charset': 'UTF-8'},
                'Body': {'Html': {'Data': None,'Charset': 'UTF-8'}}
            }
        },
        'alert': {
            'TopicArn': os.environ['SNS'],
            'Message': None,
            'Subject': 'Process {}: ' + proc
        }
    }

    return cfg

def LOGGER(env):
    """"""
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    logger = logging.getLogger(__name__)

    if env=='dev':
        level = logging.DEBUG
        feed = sys.stdout
    elif env=='qa':
        level = logging.INFO
        feed = io.StringIO()
    elif env=='prod':
        level = logging.WARNING
        feed = io.StringIO()
    else:
        raise Exception('Unknown environment.')

    handler = logging.StreamHandler(feed)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger,feed

def QUERY_GENERATOR(url,titles,locations,replace,pages=1):
    """"""
    logger = logging.getLogger(__name__)

    for title in titles:
        for location in locations:
            query = {'title': title,'location': location}
            for char,replace in replace.items():
                title = title.replace(char,replace)
                location = location.replace(char,replace)
            for page in range(pages):
                query['url'] = url.format(NUM=10*page,QRY=title,LOC=location)
                logger.info('Generating URL: {}'.format(query['url']))

                yield query

def CLEAN(item):
    """"""
    logger = logging.getLogger(__name__)

    base = re.compile(r'\s([."])(?:\s|$)')
    extra = re.compile('[^A-Za-z0-9\&\.\s]+')
    spaces = re.compile('\s{2,}')

    return base.sub(r'\1',spaces.sub(' ',extra.sub('',item))).strip().upper()

def EXTRACT(soup):
    """"""
    logger = logging.getLogger(__name__)

    url = 'www.indeed.com'
    skip = ['indeed_id','url_post']
    posts = []

    for row in soup.find_all(name='div',attrs={'class':'row'}):
        post = {'indeed_id':str(uuid.uuid4())}

        try:
            post['title'] = row.find(name='a',attrs={'data-tn-element':'jobTitle'}).text
        except:
            post['title'] = None
        try:
            post['company'] = row.find(name='a',attrs={'data-tn-element':'companyName'}).text
        except:
            post['company'] = None
        try:
            post['rating'] = row.find(name='span',attrs={'class':'ratingsContent'}).text
        except:
            post['rating'] = None
        try:
            post['city'] = row.find('div', attrs={'class': 'recJobLoc'})['data-rc-loc'].split(',')[0]
        except:
            post['city'] = None
        try:
            post['state'] = row.find('div', attrs={'class': 'recJobLoc'})['data-rc-loc'].split(',')[1]
        except:
            post['state'] = None
        try:
            post['salary'] = row.find('nobr').text
        except:
            post['salary'] = None
        try:
            post['summary'] = ' '.join([i.text for i in row.find('div',attrs={'class','summary'}).find_all('li')])
        except:
            post['summary'] = None
    #     try:
    #         post['duties'] = None
    #     except:
    #         post['duties'] = None
    #     try:
    #         post['skills'] = None
    #     except:
    #         post['skills'] = None
        try:
            post['url_post'] = url+row.find(name='a',attrs={'data-tn-element':'jobTitle'})['href']
        except:
            post['url_post'] = None
    #     try:
    #         post['url_app'] = None
    #     except:
    #         post['url_app'] = None

        for field,value in post.items():
            if (field not in skip) & (value!=None):
                post[field] = CLEAN(value)

        posts.append(post)

    return posts

def LOAD(data,url,table):
    """"""
    logger = logging.getLogger(__name__)

    # fails = []
    db = boto3.resource('dynamodb', endpoint_url=url)
    tbl = db.Table(table)
    with tbl.batch_writer() as batch:
        for item in data:
            response = batch.put_item(Item=item)
            # error handling - batch does this automatically
            # if response:
            #     fails.append(response)
    # return fails

def BODY(data):
    """"""
    logger = logging.getLogger(__name__)

    body = 'Here are today\'s job postings:<br><br>'
    template = '<li>{TITLE} at {COMPANY} in {CITY}, {STATE} - <a href=\'{URL}\'>Link</a></li>'
    groups = set((item['q_title'],item['q_location']) for item in data)
    for group in groups:
        rows = '<b>{TITLE} in {LOCATION}</b>:<br><ul>'.format(TITLE=group[0],LOCATION=group[1])
        for item in data:
            if group==(item['q_title'],item['q_location']):
                rows+=template.format(
                    URL=item['url_post'],
                    TITLE=item['title'],COMPANY=item['company'],
                    CITY=item['city'],STATE=item['state']
                )
        body+=(rows+'</ul>')

    return body

def ALERT(publish,success,err=None):
    """"""
    if success:
        publish['Subject'] = publish['Subject'].format('Success')
        publish['Message'] = 'Process success.'
    else:
        publish['Subject'] = publish['Subject'].format('Failure')
        publish['Message'] = err

    return boto3.client('sns').publish(**publish)

def EMAIL(body,package):
    """"""
    package['Message']['Body']['Html']['Data'] = body
    return boto3.client('ses').send_email(**package)

def ETL(query):
    """"""
    logger = logging.getLogger(__name__)

    dttm = datetime.datetime
    start_etl = dttm.now()
    # prep vars
    query_data = {'q_title':query['title'].upper(),'q_location':query['location'].upper()}
    posts = []
    failed_query = None
    # failed_loads = []
    # get data
    logger.info('Make get request')
    response = requests.get(query['url'])
    if response.status_code == requests.codes.ok:
        # create soup object
        query['soup'] = bs4.BeautifulSoup(response.text,'html.parser')
        # extract data
        logger.info('Transform soup HTML to data')
        posts = [{**query_data,**post} for post in EXTRACT(query['soup'])]
        # load data
        logger.info('Loading {} rows into DynamoDB'.format(len(posts)))
        LOAD(posts,**CFG['db'])
    else:
        logger.DEBUG('Failed query url: {}'.format(query['url']))
        failed_query = query

    # sleep random intervals to not get caught scraping
    browse = random.randint(2,6)
    sleep = max((browse - (dttm.now() - start_etl).seconds),0)
    logger.info('Sleeping for {} seconds'.format(sleep))
    time.sleep(sleep)

    return {
        'posts': posts,
        'failed_query': failed_query,
        # 'failed_loads': failed_loads,
    }



def HANDLER(event, context):
    """"""
    dttm = datetime.datetime
    start_run = dttm.now()
    env = 'dev'

    if not event: # event=None -> developing locally
        with open(os.path.join(os.getcwd(),'..','ref','metadata.json'),'r') as f:
            META = json.load(f)
    with open(os.path.join(os.getcwd(),'env/{}'.format(env)),'r') as f:
        os.environ.update(**json.load(f))

    LOG,FEED = LOGGER(env)
    CFG = CONFIG(env)

    # temporarily use static values -> transition to using events / API
    if env=='dev':
        fails = None
        params = {
            'titles': ['data scientist'],
            'locations': ['seattle, wa']
        }
    elif env=='prod':
        params = {
            'titles': ['data scientist','business analyst','data analyst','data engineer'],
            'locations': ['seattle, wa','austin, tx','washington, dc','richmind, va','boston, ma']
        }
    else:
        raise Exception('Unknown environment')

    try:
        QUERIES = []
        POSTS = []
        FAILED_QUERIES = []
        # FAILED_LOADS = []

        LOG.info('Setup complete - generate urls.')
        # use generator to minimize downtime between requests
        QUERIES = QUERY_GENERATOR(**params,**CFG['indeed'])
        # asynchronous execution
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(ETL, QUERIES)
            for result in results:
                try:
                    POSTS+=result['posts']
                    FAILED_QUERIES.append(result['failed_query'])
                    # FAILED_LOADS+=result['failed_loads']
                except:
                    raise

        # email summary
        LOG.info('Sending email')
        body = BODY(POSTS)
        EMAIL(body,CFG['email'])
        # alert
        LOG.info('Publishing event')
        ALERT(CFG['alert'],success=True)
        # check runtime
        runtime = (dttm.now()-start_run).seconds
        LOG.info('Job complete after {} seconds.'.format(runtime))

        return {
            'status': 'success',
            'summary': '{} posts pulled in {} seconds.'.format(len(POSTS),runtime),
            # 'data': POSTS,
            # 'fails': fails
        }

    except Exception as e:
        err = str(e)
        LOG.critical('Fatal error: {}'.format(err))
        # ALERT(CFG['alert'],success=False,err=err)
        return {
            'status': 'failure',
            'error': err
        }

#print(HANDLER(None,None))
