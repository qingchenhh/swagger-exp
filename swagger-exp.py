import json
import re
from requests.exceptions import JSONDecodeError
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
    parser.add_argument('-cookie', '--cookie', dest="cookie", default='', type=str, help="指定cookie")
    parser.add_argument('-m', '--mode', dest="mode", default='sec', type=str,
                        help="指定模式，默认是sec（只测试查询接口），也可以指定为all测试所有接口。")

    return parser.parse_args()

def print_raw(raw,url,type,host=""):
    print_str = ""
    if type=="req":
        print('>>>>>请求包>>>>>')
        print_str += raw['method'] + " " + url + " HTTP/1.1\n"
        print_str += "Host: " + host + "\n"
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
        ret = re.search('^http[s]?://(?P<host>.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?)[/]', api_data[0])
        host = ret.group('host')
        print_str = api_data[4].upper() + " " + '/'+re.sub('^http[s]?://.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?[/]','',api_data[0]) + " HTTP/1.1\n"
        print_str += "Host: " + host + "\n"
        for key, values in api_data[1].items():
            print_str += key + ": " + values + "\n"
        print_str += "\n" + api_data[3]
        print(print_str)

def Scanner(url,headers,method,proxies,verbosity,summary,data=""):
    if method == "get":
        # print(headers)
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
        ret = re.search('^http[s]?://(?P<host>.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?)[/]', url)
        host = ret.group('host')
        print_raw(rep.request.__dict__,'/'+re.sub('^http[s]?://.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?[/]','',url),type='req',host=host)
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
    if method == "post":
        parameters = {}
        if "#/definitions/" in definition:
            definition = definition.replace('#/definitions/','')
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
                                parameters[parameter] = '[]'
                            else:
                                parameters[parameter] = "string"
        elif "#/components/schemas/" in definition:
            definition = definition.replace('#/components/schemas/','')
            for i in data['components']['schemas']:
                if i == definition:
                    for parameter in data['components']['schemas'][i]['properties']:
                        # print(parameter)
                        try:
                            test1 = data['components']['schemas'][i]['properties'][parameter]
                            ref1 = test1[list(test1.keys())[0]][0]['$ref']
                            # print(ref1)
                            parameters[parameter] = get_definitions(data, ref1, 'post')
                        except Exception as ee:
                            # print(ee)
                            try:
                                ref = data['components']['schemas'][i]['properties'][parameter]['$ref']
                                parameters[parameter] = get_definitions(data,ref,'post')
                            except Exception as e:
                                try:
                                    if data['components']['schemas'][i]['properties'][parameter]['type'] == "integer":
                                        parameters[parameter] = 1
                                    elif data['components']['schemas'][i]['properties'][parameter]['type'] == 'number':
                                        parameters[parameter] = 2.0
                                    elif data['components']['schemas'][i]['properties'][parameter]['type'] == 'array':
                                        parameters[parameter] = '[]'
                                    else:
                                        parameters[parameter] = "string"
                                except Exception as type_e:
                                    parameters[parameter] = "string"
    elif method == "get":
        parameters = []
        if "#/definitions/" in definition:
            definition = definition.replace('#/definitions/','')
            for i in data['definitions']:
                if i == definition:
                    for parameter in data['definitions'][i]['properties']:
                        if data['definitions'][i]['properties'][parameter]['type'] == "integer":
                            parameters.append(parameter + "=1")
                        elif data['definitions'][i]['properties'][parameter]['type'] == 'number':
                            parameters.append(parameter + "=2.0")
                        elif data['definitions'][i]['properties'][parameter]['type'] == 'array':
                            parameters.append(parameter + "=[]")
                        else:
                            parameters.append(parameter + "=string")
        elif method == "get":
            definition = definition.replace('#/components/schemas/','')
            for i in data['components']['schemas']:
                if i == definition:
                    for parameter in data['components']['schemas'][i]['properties']:
                        if data['components']['schemas'][i]['properties'][parameter]['type'] == "integer":
                            parameters.append(parameter + "=1")
                        elif data['components']['schemas'][i]['properties'][parameter]['type'] == 'number':
                            parameters.append(parameter + "=2.0")
                        elif data['components']['schemas'][i]['properties'][parameter]['type'] == 'array':
                            parameters.append(parameter + "=[]")
                        else:
                            parameters.append(parameter + "=string")
    return parameters

def get_method(rep,path,method,url1,cookie):
    try:
        content_type = rep['paths'][path][method]['consumes'][0]
    except Exception as e:
        content_type = "text/html; charset=utf-8"
    parameters = []
    if cookie != '':
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
            'Content-Type': content_type,
            'Cookie': cookie
        }
    else:
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
                                try:
                                    type = parameter['type'] # 2.0和1.0版本
                                except:
                                    type = 'string'
                            if type == "integer":
                                default_str = 1
                            elif type == "array":
                                default_str = '[]'
                            else:
                                default_str = "string"
                        if  parameter['in'] == "header": # 参数位置在header
                            headers[parameter['name']] = str(default_str)
                        else:
                            parameters.append(parameter['name'] + "=" + str(default_str))
                new_url = url1 + path + '?' + '&'.join(parameters)
            except Exception as e:
                # print(e)
                new_url = url1 + path
        return new_url,headers,summary,"",method
    except Exception as e:
        return False

def post_method(rep,path,method,url1,cookie):
    try:
        content_type = rep['paths'][path][method]['consumes'][0]
    except Exception as e:
        content_type = "text/html; charset=utf-8"
    parameters = {}
    if cookie != '':
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
            'Content-Type': content_type,
            'Cookie': cookie
        }
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
            'Content-Type': content_type
        }
    try:
        summary = rep['paths'][path][method]['summary']
    except Exception as e:
        summary = ""
    parameters1 = {}
    try:
        # 3.0的另一种形式
        try:
            content = rep['paths'][path][method]['requestBody']['content']
            headers['Content-Type'] = list(content.keys())[0] # 获取第一个key
            definition1 = rep['paths'][path][method]['requestBody']['content'][list(content.keys())[0]]['schema']['$ref']
            parameters1 = get_definitions(rep, definition1, 'post')
        except Exception as e:
            # print(e)
            pass
        try:
            definition = rep['paths'][path][method]['parameters'][0]['schema']['$ref']
        except Exception as e:
            definition = ""
        if definition != "":
            parameters = get_definitions(rep, definition, 'post')
        else:
            # 如果没有任何参数，报错，则忽略。
            try:
                for parameter in rep['paths'][path][method]['parameters']:
                    try:
                        default_str = parameter['default']
                    except Exception as e:
                        try:
                            type = parameter['schema']['type'] # 3.0版本
                        except Exception as e:
                            try:
                                type = parameter['type'] # 2.0和1.0版本
                            except Exception as e:
                                type = "string"
                        if type == "integer":
                            default_str = 1
                        elif type == 'number':
                            default_str = 2.0
                        else:
                            default_str = "string"
                    if parameter['in'] == "header":
                        headers[parameter['name']] = str(default_str)
                    else:
                        parameters[parameter['name']] = default_str
            except Exception as pe:
                pass
        if parameters1 :
            parameters = parameters1.copy()
        if "application/json" in headers['Content-Type']:
            data = json.dumps(parameters)
        else:
            data = ""
            for key,values in parameters.items():
                data +=key+"="+str(values)+"&"
            data = data[:-1]
        new_url = url1 + path
        return new_url,headers,summary,data,method
    except Exception as e:
        return False
        # print(Style.BRIGHT + Fore.RED + "[-] 出现一小个错误！POST参数，url为：" + url + path + " , Error Message：" ,e)

def run(url,proxies,verbosity,fpath,mode,cookie):
    if cookie != '':
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
            'content-type': 'application/json',
        }
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36',
            'content-type': 'application/json',
            'Cookie': cookie
        }
    uploads = []
    downloads = []
    try:
        rep = requests.get(url=url, verify=False, headers=headers).json()
    except JSONDecodeError:
        print(Style.BRIGHT + Fore.RED + "[-] 不是有效的json接口。")
        exit()
    except Exception as e:
        print(Style.BRIGHT + Fore.RED + "[-] 程序出错了,异常信息如下：")
        print(e)
        exit()
    url1 = re.findall('^http[s]?://.+\.[0-9a-zA-Z]+[:]?[1-6]?[0-9]?[0-9]?[0-9]?[0-9]?[/]',url)[0]
    url1 = url1.rstrip('/')
    if fpath != "":
        url1 = url1 + '/' + fpath
    for path in rep['paths']:
        flag = screen(path)
        if (flag == []) and (mode != "all"):
            continue
        for method in rep['paths'][path]:
            # print(path,method)
            if method == "get":
                # 防止乱带参数而没有查询到数据，直接访问接口反而有数据的情况，不过要有brup代理才看得到。
                requests.get(url1 + path,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36'} ,proxies=proxies, verify=False)
                get_methods = get_method(rep, path, method, url1,cookie)
                if get_methods != False:
                    if 'get' in flag or (mode == "all"):
                        Scanner(get_methods[0], get_methods[1], get_methods[4], proxies, verbosity, get_methods[2], url1 + path)
                    if 'upload' in flag:
                        uploads.append(get_methods)
                    if 'download' in flag:
                        downloads.append(get_methods)
            else:
                # 防止乱带参数而没有查询到数据，直接访问接口反而有数据的情况，不过要有brup代理才看得到。
                requests.post(url1 + path,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36'}, proxies=proxies, verify=False)
                post_methods = post_method(rep, path, method, url1,cookie)
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
    run(url,proxies,args.verbosity,args.path,args.mode,args.cookie)