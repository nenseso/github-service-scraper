import requests
from bs4 import BeautifulSoup
import csv

def get_repository_star_count(repo_url):
    """
    从给定的GitHub仓库URL中获取Star数。
    能正确处理指向仓库主页的链接。
    """
    if not repo_url.startswith("https://github.com/"):
        print(f"    - 跳过非GitHub链接: {repo_url}")
        return 0
    
    try:
        response = requests.get(repo_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # GitHub仓库Star数的标准HTML结构
        repo_path = repo_url.split("github.com/")[-1].split("/tree/")[0]
        star_link = soup.find('a', href=f'/{repo_path}/stargazers')
        
        if star_link:
            star_text_element = star_link.find('span', class_='text-bold')
            if star_text_element:
                star_text = star_text_element.text.strip()
                if 'k' in star_text.lower():
                    return int(float(star_text.lower().replace('k', '')) * 1000)
                return int(star_text.replace(',', ''))
    except requests.exceptions.RequestException as e:
        print(f"    - 抓取Star数时出错 {repo_url}: {e}")
    except Exception as e:
        print(f"    - 解析Star数时出错 {repo_url}: {e}")
    return 0

def scrape_all_services(readme_url):
    """
    从GitHub README页面抓取所有第一方和第三方服务。
    """
    all_services = []
    
    # 1. 获取主仓库的URL和Star数，用于第一方服务
    main_repo_url = "https://github.com/" + "/".join(readme_url.split('/')[3:5])
    print(f"正在获取主仓库的Star数: {main_repo_url}")
    main_repo_stars = get_repository_star_count(main_repo_url)
    print(f"主仓库的Star数为: {main_repo_stars}\n")

    try:
        response = requests.get(readme_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        article = soup.find('article', class_='markdown-body')
        if not article:
            print("错误: 未能找到页面上的文章内容。")
            return []

        all_lists = article.find_all('ul')
        
        # 2. 处理第一方服务 (通常在第二个`ul`，索引为1)
        if len(all_lists) > 1:
            print("--- 正在处理第一方服务 (Available Servers) ---")
            service_list = all_lists[1]
            for item in service_list.find_all('li'):
                link = item.find('strong').find('a') if item.find('strong') else item.find('a')
                if link and link.has_attr('href'):
                    service_name = link.text.strip()
                    # 相对路径，构建完整URL
                    full_url = "https://github.com" + link['href']
                    all_services.append({'Service': service_name, 'Stars': main_repo_stars, 'URL': full_url})
                    print(f"- 已添加: {service_name} (共享Star数: {main_repo_stars})")

        # 3. 处理第三方服务 (根据XPath，在第四个`ul`，索引为3)
        if len(all_lists) > 3:
            print("\n--- 正在处理第三方服务 (Third-Party Servers) ---")
            third_party_list = all_lists[3]
            for item in third_party_list.find_all('li'):
                link = item.find('strong').find('a') if item.find('strong') else item.find('a')
                if link and link.has_attr('href'):
                    service_name = link.text.strip()
                    repo_url = link['href']
                    # 检查是否为完整的GitHub链接
                    if not repo_url.startswith('http'):
                         repo_url = "https://github.com" + repo_url
                    
                    print(f"- 正在抓取: {service_name} ({repo_url})")
                    stars = get_repository_star_count(repo_url)
                    all_services.append({'Service': service_name, 'Stars': stars, 'URL': repo_url})
                    print(f"  > Star数: {stars}")

    except requests.exceptions.RequestException as e:
        print(f"抓取主页面时出错: {e}")
    except Exception as e:
        print(f"处理页面时出错: {e}")
        
    return all_services

if __name__ == '__main__':
    target_url = 'https://github.com/modelcontextprotocol/servers/tree/main?tab=readme-ov-file'
    output_filename = 'github_all_services_sorted.csv'
    
    # 抓取所有服务
    final_service_list = scrape_all_services(target_url)

    if final_service_list:
        # 4. 按Star数从高到低排序
        print("\n--- 正在排序 ---")
        sorted_list = sorted(final_service_list, key=lambda x: x['Stars'], reverse=True)

        # 5. 写入CSV文件
        try:
            with open(output_filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['Service', 'Stars', 'URL'])
                writer.writeheader()
                writer.writerows(sorted_list)
            print(f"\n✅ 成功! 所有数据已抓取并排序，保存至 {output_filename}")
        except IOError as e:
            print(f"\n写入CSV文件时出错: {e}")
    else:
        print("\n未能抓取到任何服务信息。")