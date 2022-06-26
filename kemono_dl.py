import os, re, urllib3, argparse
from bs4 import BeautifulSoup
from math import ceil

site_sub = ''
creator_id = ''
creator_name = ''
output_folder = 'output'
download_pages = {}
dev = False

def to_beta_url(url):
    global site_sub, creator_id

    creator_id = int(re.search(r'user/([0-9]+)', url).group(1))
    site_sub = re.search(r'party/([a-z]+)', url).group(1)
    return f'http://beta.kemono.party/{site_sub}/user/{creator_id}'

def get_page_number(url):
    global creator_name

    http = urllib3.PoolManager()
    page = http.request('GET', url)

    if page.status == 200:
        soup = BeautifulSoup(page.data, features='lxml')
        text = soup.find(id='paginator-bottom').prettify()
        search = re.search(r'Showing 1 - [0-9]+ of ([0-9]+)', text)
        creator_name = re.search(r'Posts of (.+) from', soup.title.prettify()).group(1)

        if search is None:  # only one page
            return 1

        return ceil(int(search.group(1)) / 25)

    else:
        return -2

def download_file(url, file_name, post_id):
    if not os.path.isdir(output_folder):  # output folder
        os.mkdir(output_folder)

    if not os.path.isdir(f'{output_folder}//{creator_name}'):  # creator folder
        os.mkdir(f'{output_folder}//{creator_name}')

    if os.path.isfile(f'{output_folder}//{creator_name}//{post_id}-{file_name}'):  # file exists
        return

    if dev:
        print(f'Downloading: \'{creator_name}\' - {post_id} - {file_name} - {url}')
    else:
        print(f'Downloading: \'{creator_name}\' - {post_id} - {file_name}')

    if file_name.startswith('http'):
        file_name = re.search(r'/.+/(.+\..+)', url).group(1)

    http = urllib3.PoolManager()
    file = http.request('GET', f'https://beta.kemono.party/{url}')

    if file.status == 200:
        with open(f'{output_folder}//{creator_name}//{post_id}-{file_name}', 'wb') as file_out:
            file_out.write(file.data)

def main():
    global site_sub, creator_id, download_pages

    """ Creator """
    for page_url in download_pages:
        creator_url = to_beta_url(page_url)
        page_number = get_page_number(creator_url)

        print(f'Creator: \'{creator_name}\' Number of pages: {page_number}, Aprox: {page_number * 25} posts')

        if page_number < 0:
            continue

        """ Pages """
        for page in range(page_number):
            http = urllib3.PoolManager()
            source = http.request('GET', f'{creator_url}?o={page * 25}')

            if source.status == 200:
                soup = BeautifulSoup(source.data, features='lxml')
                card_list = soup.find(class_='card-list__items').prettify()
                posts_id = re.findall(r'data-id="([0-9]+)"', card_list)

                """ Posts """
                for post_id in posts_id:
                    post_url = f'https://beta.kemono.party/{site_sub}/user/{creator_id}/post/{post_id}'
                    http = urllib3.PoolManager()
                    post = http.request('GET', post_url)

                    if post.status == 200:
                        soup_post = BeautifulSoup(post.data, features='lxml')
                        post_files = soup_post.find(class_='post__files')

                        if post_files is None:
                            continue

                        search_files = re.findall(r'href="/.+">', post_files.prettify())

                        """ Files """
                        for file in search_files:
                            search = re.search('(/.+)\\?f=(.+)"', file)
                            file_name = search.group(2).replace('%20', '_')
                            download_file(search.group(1), file_name, post_id)
                    else:
                        continue
            else:
                continue

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Downloads kemono.party images')
    parser.add_argument('-i', type=str, nargs='+', help='input url or text file (one url per line)')
    parser.add_argument('-dev', help='shows extra logs')
    args = parser.parse_args()

    if args.dev:
        dev = True

    if args.i is None:
        print('No valid input')
        exit(-1)

    if 'kemono' in args.i[0]:
        download_pages = args.i
    elif '.txt' in args.i[0]:
        with open(args.i[0], 'r') as input_file:
            download_pages = input_file.readlines()
    else:
        print('No valid input')
        exit(-1)

    main()
