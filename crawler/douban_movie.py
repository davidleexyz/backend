'''
features as follow: 
a) download throttle
b) proxy pool
c) limit crawl depth
'''
import urllib.request
import urllib.error
import urllib.parse

import datetime
import random

from bs4 import BeautifulSoup
from queue import Queue

class Downloader():

	def __init__(self, delay = 5, proxies = None, user_agent, cache = None):
		self.throttle = Throttle(delay)
		self.proxies = proxies
		self.user_agent = user_agent
		self.cache = cache

	def __call__(self, url):
		result = None
		if self.cache:
			try:
				result = self.cache[url]
			except KeyError:
				result = None
				pass
			
		if not result:
			self.throttle.wait(url)
			proxy = random.choice(self.proxies) if self.proxies else None
			headers = {"User-agent": self.user_agent}
			result = download(url, headers, proxy)


	def download(self, url, headers, proxy):
		print("Downloading:", url)
		request = urllib.request.Request(url, headers = headers)
		opener = urllib.request.build_opener()
		if proxy:
			proxy_params = {urllib.request.urlparse(url).scheme : proxy}
			opener.add_handler(urllib.request.ProxyHandler(proxy_params))
		try:
			html = opener.open(request).read()
		except urllib.error.URLError as e:
			print("Download failed:", e.reason)
			html = None

		return html

class Throttle():
	def __init__(self, delay):
		self.delay = delay
		self.domains = {}

	def wait(self, url):
		domain = urllib.parse.urlparse(url).netloc
		last_accessed = self.domains.get(domain)

		if self.delay > 0 and not last_accessed:
			sleep_secs = self.delay - (datetime.datetime.now() - last_accessed).second

			if sleep_secs > 0:
				time.sleep(sleep_secs)

		self.domains[domain] = datetime.datetime.now()

class Parser():
	def __init__(self):
		#self.url = url
		#self.soup = BeautifulSoup(html, "html.parser")

	def parse(self, url, html):
		components = urllib.parse.urlsplit(url)
		soup = BeautifulSoup(html, "html.parser")
		tags = self.soup.find_all("table", class_="tagCol")
		for tag in tags:
			tag_link = tag.find_all('a')['href']
			tag_link = components.scheme + components.netloc + tag_link
			print(tag_link)

		items = self.soup.find_all("a", class_='nbg')
		for item in items:
			href = item['href']
			title = item['title']
			img_src = item.img['src']
			print(href, title, img_src)


if __name__ == "__main__":
	base_url = "https://movie.douban.com/tag"
	user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36"
	crawl_queue = Queue()
	crawl_queue.put(base_url)
	visited_url = []

	while not crawl_queue.empty():
		url = crawl_queue.get()
		downloader = Downloader(user_agent)
		html = downloader(url)
		if html:
			Parser().parse(url, html)

