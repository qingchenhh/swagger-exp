import json
import re
import requests
import argparse
from colorama import init,Fore,Style

import warnings
warnings.filterwarnings('ignore')

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u','--url',dest="url",required=True, type=str,help="Please enter a url.(e.g. -u http://127.0.0.1/v2/api-docs)")
    parser.add_argument('-p', '--proxy', dest="proxy", type=str,help="Please enter an HTTP proxy address.(e.g. -p http://127.0.0.1:8080)")
    parser.add_argument('-v', '--verbosity', dest="verbosity", default='0', type=str,
                        help="Verbosity level: 0 or 1 (default 0)")
    parser.add_argument('-path', '--path', dest="path", default='', type=str,
                        help="指定路径，默认api是根路径拼接，如http://xxx.xx/user/api，但是实际路径可能是http://xxx.xx/admin/user/api，那么这个admin就需要该参数来指定。")

    return parser.parse_args()

def Scanner(url,content_type,method,proxies,verbosity,summary,data=""):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
        'Content-Type': content_type
    }
    if method == "get":
        rep = requests.get(url,headers=headers,verify=False,proxies=proxies)
        if verbosity == '1':
            print(Style.BRIGHT + Fore.GREEN + '[+] 发送一条api测试:')
            print('URL：' + url)
            print('接口说明：' + summary)
            print('请求方式：GET')
            print('Content-Type：' + content_type)
            print('响应状态码：' + str(rep.status_code))
            print('响应内容：' + rep.content.decode())
        else:
            print(Style.BRIGHT + Fore.GREEN + '[+] 发送一条api测试，请求方式：GET，' + ' URL：' + data + ' ，响应状态码：'+ str(rep.status_code))
    else:
        rep = requests.post(url,headers=headers,verify=False,data=data,proxies=proxies)
        if verbosity == '1':
            print(Style.BRIGHT + Fore.GREEN + '[+] 发送一条api测试:')
            print('URL：' + url)
            print('接口说明：' + summary)
            print('请求方式：POST')
            print('请求参数：' + data)
            print('Content-Type：' + content_type)
            print('响应状态码：' + str(rep.status_code))
            print('响应内容：' + rep.content.decode())
        else:
            print(Style.BRIGHT + Fore.GREEN + '[+] 发送一条api测试，请求方式：POST，' + ' URL：' + url + ' ，响应状态码：' + str(
                rep.status_code))

def screen(path):
    str = path.lower()
    str_list = str.split('/')
    flag = []
    for i in str_list:
        if i.startswith('get') or i.startswith('query') or i.startswith('select') or i.startswith('search') or i.startswith('show') or i.startswith('list') or (i=="info"):
            flag.append('get')
        elif i.find('upload') != -1 or i.find('fileupload') != -1or i.find('uploadfile') != -1 or i.find('uploads') != -1:
            flag.append('upload')
        elif i.find('download') != -1 or i.find('filedownload') != -1 or i.find('downloadfile') != -1 or i.find('downloads') != -1:
            flag.append('download')
    return flag

def get_definitions(data,definition,method):
    definition = definition.replace('#/definitions/','')
    if method == "post":
        parameters = {}
        for i in data['definitions']:
            if i == definition:
                for parameter in data['definitions'][i]['properties']:
                    if data['definitions'][i]['properties'][parameter]['type'] == "integer":
                        parameters[parameter] = 1
                    elif data['definitions'][i]['properties'][parameter]['type'] == 'number':
                        parameters[parameter] = 2.0
                    elif data['definitions'][i]['properties'][parameter]['type'] == 'array':
                        parameters[parameter] = 'array'
                    else:
                        parameters[parameter] = "string"
    elif method == "get":
        parameters = []
        for i in data['definitions']:
            if i == definition:
                for parameter in data['definitions'][i]['properties']:
                    if data['definitions'][i]['properties'][parameter]['type'] == "integer":
                        parameters.append(parameter + "=1")
                    elif data['definitions'][i]['properties'][parameter]['type'] == 'number':
                        parameters.append(parameter + "=2.0")
                    elif data['definitions'][i]['properties'][parameter]['type'] == 'array':
                        parameters.append(parameter + "=array")
                    else:
                        parameters.append(parameter + "=string")
    return parameters

def get_method(rep,path,method,url1):
    try:
        content_type = rep['paths'][path][method]['consumes'][0]
    except Exception as e:
        content_type = "text/html; charset=utf-8"
    parameters = []
    try:
        summary = rep['paths'][path][method]['summary']
    except Exception as e:
        summary = ""
    try:
        if re.search('\{.*?\}', path):
            # parameter = re.sub('\{.*?\}', '1', path)
            parameter = re.sub('\{', '', path)
            parameter = re.sub('\}', '', parameter)
            new_url = url1 + parameter
        else:
            try:
                is_parameters = rep['paths'][path][method]['parameters']
                try:
                    definition = rep['paths'][path][method]['parameters'][0]['schema']['$ref']
                except Exception as e:
                    definition = ""
                if definition != "":
                    parameters = get_definitions(rep, definition, 'get')
                else:
                    for parameter in rep['paths'][path][method]['parameters']:
                        if parameter['type'] == "integer":
                            parameters.append(parameter['name'] + "=1")
                        else:
                            parameters.append(parameter['name'] + "=string")
                new_url = url1 + path + '?' + '&'.join(parameters)
            except Exception as e:
                new_url = url1 + path
        return new_url,content_type,summary
    except Exception as e:
        return False

def post_method(rep,path,method,url1):
    try:
        content_type = rep['paths'][path][method]['consumes'][0]
    except Exception as e:
        content_type = "text/html; charset=utf-8"
    parameters = {}
    try:
        summary = rep['paths'][path][method]['summary']
    except Exception as e:
        summary = ""
    try:
        try:
            definition = rep['paths'][path][method]['parameters'][0]['schema']['$ref']
        except Exception as e:
            definition = ""
        if definition != "":
            parameters = get_definitions(rep, definition, 'post')
        else:
            for parameter in rep['paths'][path][method]['parameters']:
                if parameter['type'] == "integer":
                    parameters[parameter['name']] = 1
                elif parameter['type'] == 'number':
                    parameters[parameter['name']] = 2.0
                else:
                    parameters[parameter['name']] = "string"
        data = json.dumps(parameters)
        new_url = url1 + path
        return new_url,content_type,summary,data
    except Exception as e:
        return False
        # print(Style.BRIGHT + Fore.RED + "[-] 出现一小个错误！POST参数，url为：" + url + path + " , Error Message：" ,e)
        pass

def print_api(lists):
    for i in lists:
        print('*'*50)
        if len(i) == 3:
            print('URL：' + i[0])
            print('接口说明：' + i[2])
            print('请求方式：GET')
            print('Content-Type：' + i[1])
        elif len(i) == 4:
            print('URL：' + i[0])
            print('接口说明：' + i[2])
            print('请求方式：POST')
            print('Content-Type：' + i[1])
            print('请求参数：' + i[3])

def run(url,proxies,verbosity,fpath):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
        'content-type': 'application/json'
    }
    uploads = []
    downloads = []
    rep = requests.get(url=url, verify=False, headers=headers).json()
    url1 = re.findall('^http[s]?://.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?[/]',url)[0]
    url1 = url1.rstrip('/')
    if fpath != "":
        url1 = url1 + '/' + fpath
    for path in rep['paths']:
        flag = screen(path)
        if flag == []:
            continue
        for method in rep['paths'][path]:
            if method == "get":
                get_methods = get_method(rep, path, method, url1)
                if get_methods != False:
                    if 'get' in flag:
                        Scanner(get_methods[0], get_methods[1], 'get', proxies, verbosity, get_methods[2], url1 + path)
                    if 'upload' in flag:
                        uploads.append(get_methods)
                    if 'download' in flag:
                        downloads.append(get_methods)
            elif method == "post":
                post_methods = post_method(rep, path, method, url1)
                if post_methods != False:
                    if 'get' in flag:
                        Scanner(post_methods[0], post_methods[1], 'post', proxies, verbosity, post_methods[2], post_methods[3])
                    if 'upload' in flag:
                        uploads.append(post_methods)
                    if 'download' in flag:
                        downloads.append(post_methods)
            else:
                print(Style.BRIGHT + Fore.RED + "[-] 请求方法既不是GET也不是POST！")

    if uploads != []:
        print(Style.BRIGHT + Fore.GREEN + "\n[+] ===发现疑似上传接口！请人为验证并手动利用。===")
        print_api(uploads)
    if downloads != []:
        print(Style.BRIGHT + Fore.GREEN + "\n[+] ===发现疑似下载接口！请人为验证并手动利用。===")
        print_api(downloads)

if __name__ == '__main__':
    init(autoreset=True)
    args = args()
    url = args.url if args.url[-1]!='/' else args.url[:-1]
    proxies = {'http': args.proxy, 'https': args.proxy}
    run(url,proxies,args.verbosity,args.path)