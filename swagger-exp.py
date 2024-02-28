import json
import re
import requests
import argparse
from colorama import init,Fore,Style

import warnings
warnings.filterwarnings('ignore')

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u','--url',dest="url",required=True, type=str,help="指定测试的URL(e.g. -u http://127.0.0.1/v2/api-docs)")
    parser.add_argument('-p', '--proxy', dest="proxy", type=str,help="设置代理(e.g. -p http://127.0.0.1:8080)")
    parser.add_argument('-v', '--verbosity', dest="verbosity", default='0', type=str,
                        help="输出信息级别: 0 or 1 (default 0)")
    parser.add_argument('-path', '--path', dest="path", default='', type=str,
                        help="指定路径，默认api是根路径拼接，如http://xxx.xx/user/api，但是实际路径可能是http://xxx.xx/admin/user/api，那么这个admin就需要该参数来指定。")
    parser.add_argument('-m', '--mode', dest="mode", default='sec', type=str,
                        help="指定模式，默认是sec（只测试查询接口），也可以指定为all测试所有接口。")

    return parser.parse_args()

def print_raw(raw,url,type):
    print_str = ""
    if type=="req":
        print('>>>>>请求包>>>>>')
        print_str += raw['method'] + " " + url + " HTTP/1.1\n"
        headers = raw['headers']
        for key,values in headers.items():
            print_str += key + ": " + values + "\n"
        if raw['body'] != None:
            print_str += "\n" + str(raw['body'])
        else:
            print_str += "\n"
    elif type=="rep":
        print('<<<<<响应包<<<<<')
        print_str += "HTTP/1.1 " + str(raw['status_code']) + "\n"
        headers = raw['headers']
        for key, values in headers.items():
            print_str += key + ": " + values + "\n"
        print_str += "\n" + raw['_content'].decode('utf-8')
    print(print_str)

def print_api(data):
    for api_data in data:
        print("========================\n接口：" + api_data[0])
        print("描述：" + api_data[2])
        print("请求包：")
        print_str = api_data[4].upper() + " " + '/'+re.sub('^http[s]?://.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?[/]','',api_data[0]) + " HTTP/1.1\n"
        for key, values in api_data[1].items():
            print_str += key + ": " + values + "\n"
        print_str += "\n" + api_data[3]
        print(print_str)

def Scanner(url,headers,method,proxies,verbosity,summary,data=""):
    if method == "get":
        rep = requests.get(url,headers=headers,verify=False,proxies=proxies,allow_redirects=False)
    elif method == "options":
        rep = requests.options(url, headers=headers, verify=False, data=data, proxies=proxies,
                               allow_redirects=False)
    elif method == "put" and (args.mode == "all"):
        rep = requests.put(url, headers=headers, verify=False, data=data, proxies=proxies, allow_redirects=False)
    elif method == "post":
        rep = requests.post(url, headers=headers, verify=False, data=data, proxies=proxies, allow_redirects=False)
    else:
        print(Style.BRIGHT + Fore.RED + "[-] 暂不支持的请求类型！请求类型为：" + method)
        return False
    if verbosity == '1':
        print(Style.BRIGHT + Fore.GREEN + '[+] =========' + url + '=========')
        print_raw(rep.request.__dict__,'/'+re.sub('^http[s]?://.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?[/]','',url),type='req')
        print_raw(rep.__dict__, '/'+re.sub('^http[s]?://.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?[/]','',url), type='rep')
    else:
        print(Style.BRIGHT + Fore.GREEN + '[+] 发送一条'+ method.upper() +'请求，' + ' URL：' + url + ' ，响应状态码：'+ str(rep.status_code))

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
                    # print(parameter)
                    try:
                        ref = data['definitions'][i]['properties'][parameter]['$ref']
                        parameters[parameter] = get_definitions(data,ref,'post')
                    except Exception as e:
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
        'Content-Type': content_type
    }
    try:
        summary = rep['paths'][path][method]['summary']
    except Exception as e:
        summary = ""
    try:
        if re.search('\{.*?\}', path):
            # parameter = re.sub('\{.*?\}', '1', path)
            # parameter = re.sub('\{', '', path)
            # parameter = re.sub('\}', '', parameter)
            new_url = url1 + path
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
                        try:
                            default_str = parameter['default'] # 获取默认值
                        except Exception as e:
                            # print(parameter['type'])
                            try:
                                type = parameter['schema']['type'] # 3.0版本
                            except Exception as e:
                                type = parameter['type'] # 2.0和1.0版本
                            if type == "integer":
                                default_str = 1
                            else:
                                default_str = "string"
                        if  parameter['in'] == "header": # 参数位置在header
                            headers[parameter['name']] = default_str
                        else:
                            parameters.append(parameter['name'] + "=" + str(default_str))
                new_url = url1 + path + '?' + '&'.join(parameters)
            except Exception as e:
                new_url = url1 + path
        return new_url,headers,summary,"",method
    except Exception as e:
        return False

def post_method(rep,path,method,url1):
    try:
        content_type = rep['paths'][path][method]['consumes'][0]
    except Exception as e:
        content_type = "text/html; charset=utf-8"
    parameters = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
        'Content-Type': content_type
    }
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
                try:
                    default_str = parameter['default']
                except Exception as e:
                    try:
                        type = parameter['schema']['type'] # 3.0版本
                    except Exception as e:
                        type = parameter['type'] # 2.0和1.0版本
                    if type == "integer":
                        default_str = 1
                    elif type == 'number':
                        default_str = 2.0
                    else:
                        default_str = "string"
                if parameter['in'] == "header":
                    headers[parameter['name']] = default_str
                else:
                    parameters[parameter['name']] = default_str
        if "application/json" in content_type:
            data = json.dumps(parameters)
        else:
            data = ""
            for key,values in parameters.items():
                data +=key+"="+str(values)+"&"
            data = data[:-1]
        new_url = url1 + path
        return new_url,headers,summary,data,method
    except Exception as e:
        # print(e)
        return False
        # print(Style.BRIGHT + Fore.RED + "[-] 出现一小个错误！POST参数，url为：" + url + path + " , Error Message：" ,e)

def run(url,proxies,verbosity,fpath,mode):
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
        if (flag == []) and (mode != "all"):
            continue
        for method in rep['paths'][path]:
            if method == "get":
                # 防止乱带参数而没有查询到数据，直接访问接口反而有数据的情况，不过要有brup代理才看得到。
                requests.get(url1 + path,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36'} ,proxies=proxies)
                get_methods = get_method(rep, path, method, url1)
                if get_methods != False:
                    if 'get' in flag or (mode == "all"):
                        Scanner(get_methods[0], get_methods[1], get_methods[4], proxies, verbosity, get_methods[2], url1 + path)
                    if 'upload' in flag:
                        uploads.append(get_methods)
                    if 'download' in flag:
                        downloads.append(get_methods)
            else:
                # 防止乱带参数而没有查询到数据，直接访问接口反而有数据的情况，不过要有brup代理才看得到。
                requests.post(url1 + path,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36'}, proxies=proxies)
                post_methods = post_method(rep, path, method, url1)
                if post_methods != False:
                    if ('get' in flag) or (mode == "all"):
                        Scanner(post_methods[0], post_methods[1], post_methods[4], proxies, verbosity, post_methods[2], post_methods[3])
                    if 'upload' in flag:
                        uploads.append(post_methods)
                    if 'download' in flag:
                        downloads.append(post_methods)
            # else:
            #     print(Style.BRIGHT + Fore.RED + "[-] 请求方法既不是GET也不是POST！")

    if uploads != []:
        print(Style.BRIGHT + Fore.GREEN + "\n[+] ===发现疑似上传接口！请人为验证并手动利用。===")
        print(Style.BRIGHT + Fore.GREEN + "[+] !!!注意！文件上传构造的数据包并不准确，需要手动构造。!!!")
        print_api(uploads)
    if downloads != []:
        print(Style.BRIGHT + Fore.GREEN + "\n[+] ===发现疑似下载接口！请人为验证并手动利用。===")
        print_api(downloads)

if __name__ == '__main__':
    init(autoreset=True)
    args = args()
    url = args.url if args.url[-1]!='/' else args.url[:-1]
    proxies = {'http': args.proxy, 'https': args.proxy}
    run(url,proxies,args.verbosity,args.path,args.mode)