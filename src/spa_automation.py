#!/usr/bin/env python3

import argparse, asyncio, os, re, tempfile
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright._impl._errors import TargetClosedError as PlaywrightTargetClosedError, Error as PlaywrightError

# ----------------------------------------

def print_info(text):
	print(f"[+] {text}")

def print_alert(text):
	print(f"[!] {text}")

def print_action(text):
	return input(f"[?] {text}")

def print_download(text):
	print(f"[>] {text}")

def print_error(text):
	print(f"[-] {text}")

# ----------------------------------------

def unique(sequence, sort = False): # unique sort
	seen = set()
	array = [x for x in sequence if not (x in seen or seen.add(x))]
	if sort and array:
		array = sorted(array, key = str.casefold, reverse = False) # sort by name ascending
	return array

def read_array(file, sort = False):
	array = []
	if not os.path.isfile(file):
		print_error(f"\"{file}\" is not a file or does not exists")
	elif not os.access(file, os.R_OK):
		print_error(f"\"{file}\" file does not have a read permission")
	elif not os.stat(file).st_size > 0:
		print_error(f"\"{file}\" file is empty")
	else:
		with open(file, "r", encoding = "UTF-8") as stream:
			for line in stream:
				line = line.strip()
				if line:
					array.append(line)
	return unique(array, sort)

def directory_create(directory):
	success = True
	if not os.path.exists(directory):
		try:
			os.mkdir(directory)
		except Exception:
			success = False
			print_error(f"Cannot create \"{directory}\" directory")
	return success

def directory_create_tmp():
	return tempfile.mkdtemp(prefix = "spa_automation_", suffix = "_session", dir = os.getcwd()) # create a new random directory in the current working directory and return its absolute path

# ----------------------------------------

def get_extra_value(numeric = False, **kwargs):
	value = kwargs["value"] if kwargs and "value" in kwargs else ""
	if numeric:
		if not value:
			value = -1
		elif not value.isdigit():
			value = -1
			print_error("Extra value must be a numeric greater than or equal to zero")
		else:
			value = int(value)
	return value

# ----------------------------------------

class Sandbox:

	def __init__(self, browser, session, password, wait, dev, proxy):
		self.browser    = browser
		self.session    = os.path.abspath(session)
		self.dev        = dev
		self.proxy      = proxy
		self.playwright = None
		self.context    = None
		self.timeout    = 30 * 1000 # default timeout for all browser actions
		self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" # change the user agent as necessary
		self.settings   = {
			"downloads"   : os.path.join(self.session, "downloads"), # downloads directory
			"password"    : password, # SPA setup and unlock password
			"wait_time"   : wait, # default wait time
			"wait_state"  : "load",
			"css_root"    : "body",
			"css_submit"  : "input[type=submit]",
			"css_checkbox": "input[type=checkbox]",
			"css_text"    : "input[type=text]",
			"css_email"   : "input[type=email]",
			"css_password": "input[type=password]",
			"home_page"   : "home.html", # SPA home page
			"url_base"    : "https://wallet.uniswap.org", # SPA base url | specify
			"url_dapp"    : "https://app.uniswap.org" if not self.dev else "https://app.uniswap.org" # use "self.dev" throughout the code to switch between environments
		} # change the default variables as necessary

	async def browser_start(self):
		self.playwright = await async_playwright().start()
		browsers = {
			"chromium": self.playwright.chromium,
			"firefox" : self.playwright.firefox
		}
		self.context = await browsers[self.browser].launch_persistent_context(
			headless            = False,
			handle_sigint       = False, # do not terminate on SIGINT (CTRL + C)
			bypass_csp          = False,
			ignore_https_errors = True,
			java_script_enabled = True,
			accept_downloads    = True,
			proxy               = { "server": self.proxy } if self.proxy else None,
			user_agent          = self.user_agent,
			user_data_dir       = self.session,
			downloads_path      = self.settings["downloads"],
			args                = [],
			firefox_user_prefs  = {
				"media.navigator.permission.disabled": True # for KYC purposes
			}
		)
		if self.browser != "firefox":
			await self.context.grant_permissions(["camera"]) # for KYC purposes
		self.context.set_default_timeout(self.timeout)
		# --------------------------------
		print_info(f"Running a {self.browser} sandbox...")

	async def browser_stop(self):
		await self.context.close()
		await self.playwright.stop()

	# ------------------------------------ GENERIC BUILDING BLOCKS (SINGLE ACTION)

	async def __new_page(self):
		return await self.context.new_page()

	async def __close(self, page, close = True):
		if close:
			await page.close()

	async def __wait(self, page, override = -1):
		if override > 0:
			await asyncio.sleep(override) # override the default wait time
		elif self.settings["wait_time"] > 0:
			await asyncio.sleep(self.settings["wait_time"]) # default wait time
		await page.wait_for_load_state(self.settings["wait_state"])

	async def __goto(self, page, url):
		response = await page.goto(url)
		await self.__wait(page) # web pages usually need some time to fully load
		return response

	async def __goto_spa(self, page, path = ""):
		if not path:
			path = self.settings["home_page"]
		return await self.__goto(page, f"{self.settings['url_base']}/{path.lstrip('/')}")

	async def __save_file(self, download):
		filename = self.settings["downloads"] + os.path.sep + download.suggested_filename
		await download.save_as(filename)
		print_download(f"Downloaded file was saved at \"{filename}\"")

	def __handle_downloads(self, page):
		page.on("download", self.__save_file)

	def __accept_popups(self, page, accept = True):
		page.on("dialog", lambda dialog: dialog.accept() if accept else dialog.dismiss())

	# ------------------------------------

	def __locate(self, page, css, text = ""):
		return page.locator(css).filter(has_text = text) # you can also pass a regular expression compiled with "re.compile()" as "text"

	async def __get_text(self, page, css, text = ""):
		return await self.__locate(page, css, text).text_content()

	async def __get_size(self, page, css, text = ""):
		return len(await self.__get_text(page, css, text))

	async def __is_enabled(self, page, css, text = ""):
		return await self.__locate(page, css, text).is_enabled() # readonly also returns "False"

	async def __is_visible(self, page, css, text = ""):
		return await self.__locate(page, css, text).is_visible()

	async def __fill(self, page, value, css = ""):
		if not css:
			css = self.settings["css_text"]
		await self.__locate(page, css).fill(value)

	async def __fill_sequentially(self, page, value, css = ""):
		if not css:
			css = self.settings["css_text"]
		for i in range(len(value)):
			await self.__locate(page, f"{css}>>nth={i}").press_sequentially(value[i])

	async def __tick(self, page, css = ""):
		if not css:
			css = self.settings["css_checkbox"]
		await self.__locate(page, css).click()

	async def __submit(self, page, css = "", text = ""):
		if not css:
			css = self.settings["css_submit"]
		await self.__locate(page, css, text).click()
		await self.__wait(page) # web forms usually need some time to be processed

	# ------------------------------------ GENERIC BUILDING BLOCKS (MULTIPLE ACTIONS)

	async def __create_password_submit(self, page, password = "", css = "", text = ""): # fill in twice
		if not password:
			password = self.settings["password"]
		for i in range(2):
			await self.__fill(page, password, f"{self.settings['css_password']}>>nth={i}")
		await self.__submit(page, css, text)

	async def __fill_password_submit(self, page, password = "", css = "", text = ""): # fill in once
		if not password:
			password = self.settings["password"]
		await self.__fill(page, password, self.settings["css_password"])
		await self.__submit(page, css, text)

	async def __fill_sequentially_password_submit(self, page, password, css = "", text = ""): # fill in a mnemonic where each word has a separate input field | pass an array as "password"
		await self.__fill_sequentially(page, password, self.settings["css_password"])
		await self.__submit(page, css, text)

	async def __fill_email_submit(self, page, email, css = "", text = ""):
		await self.__fill(page, email, self.settings["css_email"])
		await self.__submit(page, css, text)

	async def __fill_text_submit(self, page, value, css = "", text = ""):
		await self.__fill(page, value)
		await self.__submit(page, css, text)

	async def __fill_sequentially_text_submit(self, page, value, css = "", text = ""): # fill in an OTP where each digit has a separate input field | pass a string as "value"
		await self.__fill_sequentially(page, value)
		await self.__submit(page, css, text)

	async def __get_cookie(self, name, url = None): # get a [session] cookie
		cookie = ""
		name = name.lower()
		for entry in await self.context.cookies(url):
			if entry["name"].lower() == name:
				cookie = entry["value"]
				break
		return cookie
	
	# ------------------------------------ WEBHOOK BUILDING BLOCKS

	async def __webhook_start(self): # collaborator server / email service
		page = await self.__new_page()
		await self.__goto(page, "https://webhook.site")
		# --------------------------------
		self.__accept_popups(page, True)
		await self.__submit(page, "a[id=optionsDropdown]", "more")
		await self.__submit(page, "a", "delete all requests") # delete all previous collaborator requests and emails
		# --------------------------------
		email = await self.__get_text(page, "code", re.compile(r".+@emailhook\.site", re.IGNORECASE))
		print_alert(f"Webhook email: {email}")
		dns = (await self.__get_text(page, "code", re.compile(r".+\.dnshook\.site", re.IGNORECASE))).lstrip("*.")
		print_alert(f"Webhook DNS: {dns}")
		# --------------------------------
		return page, email, dns

	async def __webhook_get_email_text(self, page, timeout = -1):
		timeout = timeout * 1000 if timeout > 0 else self.timeout # override the default timeout
		print_info(f"Waiting {timeout / 1000} sec for the webhook to arrive...")
		return await self.__locate(page, "pre>>nth=0").text_content(timeout = timeout)

	# ------------------------------------ METAMASK FLOWS

	async def __created(self, page):
		return not await self.__is_visible(page, "button", "create a new wallet")

	async def __is_created(self, page):
		created = await self.__created(page)
		if not created:
			print_error("Wallet is not created")
		return created

	async def __is_not_created(self, page):
		created = await self.__created(page)
		if created:
			print_error("Wallet is already created")
		return not created

	async def __locked(self, page):
		return await self.__is_visible(page, "button", "unlock")

	async def __unlock(self, page, password = ""):
		if await self.__locked(page):
			await self.__fill_password_submit(page, password, "button", "unlock")
			if await self.__is_visible(page, "button[data-testid=popover-close]"): # close a pop-up
				await self.__submit(page, "button[data-testid=popover-close]")

	async def __lock(self, page):
		if not await self.__locked(page):
			await self.__goto_spa(page, f"{self.settings['home_page']}#lock")

	# ------------------------------------

	async def open(self, **kwargs):
		page = await self.__new_page()
		await self.__goto_spa(page)
		# await self.__close(page)

	async def create(self, **kwargs):
		page = await self.__new_page()
		await self.__goto_spa(page)
		if await self.__is_not_created(page):
			await self.__tick(page)
			await self.__submit(page, "button", "create a new wallet")
			await self.__submit(page, "button", "no thanks")
			await self.__tick(page)
			await self.__create_password_submit(page, css = "button", text = "create a new wallet")
			await self.__submit(page, "button", "remind me later")
			await self.__tick(page)
			await self.__submit(page, "button", "skip")
			await self.__submit(page, "button", "got it")
			await self.__submit(page, "button", "next")
			await self.__submit(page, "button", "done")
			await self.__submit(page, "button[data-testid=popover-close]")
		# await self.__close(page)

	async def existing(self, **kwargs):
		page = await self.__new_page()
		await self.__goto_spa(page)
		if await self.__is_not_created(page):
			await self.__tick(page)
			await self.__submit(page, "button", "import an existing wallet")
			await self.__submit(page, "button", "no thanks")
			mnemonic = get_extra_value(**kwargs) # pass a mnemonic as an extra value
			if not mnemonic:
				print_error("Mnemonic is required, please pass it manually using the \"-v\" option")
			else:
				await self.__fill_sequentially_password_submit(page, mnemonic.split(" "), "button", "confirm Secret Recovery Phrase")
				await self.__tick(page)
				await self.__create_password_submit(page, css = "button", text = "import my wallet")
				await self.__submit(page, "button", "got it")
				await self.__submit(page, "button", "next")
				await self.__submit(page, "button", "done")
				await self.__submit(page, "button[data-testid=popover-close]")
		# await self.__close(page)

	async def unlock(self, **kwargs):
		page = await self.__new_page()
		await self.__goto_spa(page)
		if await self.__is_created(page):
			password = get_extra_value(**kwargs) # pass a [wrong] password as an extra value
			await self.__unlock(page, password)
		# await self.__close(page)

	async def unlock_brute_force(self, **kwargs):
		page = await self.__new_page()
		await self.__goto_spa(page)
		if await self.__is_created(page):
			await self.__lock(page)
			wordlist = get_extra_value(**kwargs) # pass a wordlist as an extra value
			if not wordlist:
				print_error("Wordlist is required, please pass it manually using the \"-v\" option")
			else:
				wordlist = read_array(wordlist)
				print_info(f"Number of words loaded: {len(wordlist)}")
				for password in wordlist:
					await self.__fill_password_submit(page, password, "button", "unlock")
					if not await self.__locked(page):
						print_alert(f"Unlocked: {password}")
						break
		# await self.__close(page)

	async def idle_lock(self, **kwargs):
		page = await self.__new_page()
		await self.__goto_spa(page)
		if await self.__is_created(page):
			await self.__unlock(page)
			await self.__submit(page, "button[data-testid=account-options-menu-button]")
			await self.__submit(page, "button[data-testid=global-menu-settings]")
			await self.__submit(page, "button", "advanced")
			await self.__fill(page, "2", "input[id=autoTimeout]") # 2 minutes
			await self.__submit(page, "button[data-testid=auto-lockout-button]")
			wait_time = 2 * 60 + 5 # 2 minutes and 5 seconds
			print_info(f"Waiting {wait_time} sec for the wallet to auto-lock...")
			await self.__wait(page, wait_time)
			await self.__goto_spa(page)
			if not await self.__locked(page):
				print_alert("Auto-lock does not work properly")
		# await self.__close(page)

	async def access_control(self, **kwargs):
		page = await self.__new_page()
		await self.__goto_spa(page)
		if await self.__is_created(page):
			state = get_extra_value(**kwargs).lower() # pass a lock state as an extra value
			if state == "locked":
				await self.__lock(page)
			elif state == "unlocked":
				await self.__unlock(page)
			else:
				print_error("Lock state is required, please pass \"locked\" or \"unlocked\" manually using the \"-v\" option")
				return 0
			# ----------------------------
			pages = [
				"/home.html"
			]
			fragments = [
				"#new-account",
				"#new-account/connect",
				"#notifications",
				"#restore-vault",
				"#seed",
				"#send",
				"#settings",
				"#settings/about-us",
				"#settings/advanced",
				"#settings/alerts",
				"#settings/contact-list",
				"#settings/contact-list/add-contact",
				"#settings/contact-list/edit-contact",
				"#settings/contact-list/view-contact",
				"#settings/general",
				"#settings/networks",
				"#settings/networks/form",
				"#settings/security",
				"#snaps",
				"#snaps/view",
				"#swaps",
				"#swaps/awaiting-signatures",
				"#swaps/build-quote",
				"#swaps/loading-quotes",
				"#swaps/maintenance",
				"#swaps/notification-page",
				"#swaps/prepare-swap-page",
				"#swaps/smart-transaction-status",
				"#swaps/swaps-error",
				"#swaps/view-quote"
			]
			# ----------------------------
			paths = []
			for page in pages:
				page = page.split(".html", 1)[0].strip("/")
				if page:
					page = f"/{page}.html"
					paths.append(page)
					for fragment in fragments:
						fragment = fragment.rsplit("#", 1)[-1].strip("/")
						if fragment:
							paths.append(f"{page}#{fragment}")
			paths = unique(paths)
			print_info(f"State: {state}")
			print_info(f"Number of URLs: {len(paths)}")
			# ----------------------------
			success = True
			for path in paths: # reusing the same page on success "False"
				if success:
					tmp = await self.__new_page()
				success = False
				await self.__goto_spa(tmp, path)
				size = await self.__get_size(tmp, "div[id=app-content]") if await self.__is_visible(tmp, "div[id=app-content]") else 0
				if size < 1 or (state == "locked" and await self.__locked(tmp)) or (state == "unlocked" and await self.__is_visible(tmp, "div[class=wallet-overview__balance]")):
					continue
				success = True
				print_alert(f"Size: [{size:>5}] | URL: {self.settings['url_base']}{path}")
			if not success:
				await self.__close(tmp)
			# ----------------------------
		# await self.__close(page)

# ----------------------------------------

class Test:

	def __init__(self, browser, session, password, test, value, wait, dev, proxy):
		session            = self.__get_environment(session)
		self.event_loop    = self.__get_runtime()
		self.test          = test
		self.value         = value
		self.sandbox       = Sandbox(
			browser  = browser,
			session  = session,
			password = password,
			wait     = wait,
			dev      = dev,
			proxy    = proxy
		)

	def __get_environment(self, session):
		if not session:
			session = directory_create_tmp()
			print_info(f"User session directory was not specified, creating a new \"{session}\" random directory...")
			print_info(f"Next time, to continue using the same browser session, run the following command:\n    python3 spa_automation.py -s \"{session}\"")
		elif not directory_create(session):
			exit()
		return session

	def __get_runtime(self):
		asyncio.set_event_loop(asyncio.new_event_loop())
		return asyncio.get_event_loop()

	def run(self):
		try:
			print_info("Press CTRL + C to exit early")
			self.event_loop.run_until_complete(self.sandbox.browser_start())
			self.event_loop.run_until_complete(getattr(self.sandbox, self.test)(value = self.value))
			print_action("Done, press any key to exit...")
		except (PlaywrightTargetClosedError, PlaywrightTimeoutError, PlaywrightError, KeyboardInterrupt) as ex:
			print(ex)
		finally:
			self.event_loop.run_until_complete(self.sandbox.browser_stop())
			self.event_loop.stop()
			self.event_loop.close()

# ----------------------------------------

class MyParser(argparse.ArgumentParser):

	def __init__(self, *args, **kwargs):
		super(MyParser, self).__init__(*args, **kwargs)
		self.browsers   = ["chromium", "firefox"]
		self.password   = "Password123!" # browser extension setup and unlock password
		self.tests      = ["open", "create", "existing", "unlock", "brute_force_unlock", "idle_lock", "access_control"] # to run new tests, add the flows (method names) inside this array
		self.wait       = 2 # default wait time

	def error(self, message):
		print_error(f"Error: {message}")
		exit()

	def print_help(self):
		print("SPA Automation v1.1 ( https://github.com/ivan-sincek/browser-extension-automation )")
		print("")
		print("Usage: python3 spa_automation.py [-b browser] [-s session] [-p password] [-t test] [-v value] [-w wait] [--dev] [-x proxy]")
		print("")
		print("DESCRIPTION")
		print("    SPA automation script")
		print("BROWSER")
		print("    Browser to run")
		print(f"    Default: {self.browsers[0]}")
		print(f"    -b, --browser = {(' | ').join(self.browsers)}")
		print("SESSION")
		print("    User session directory")
		print("    Default: random")
		print("    -s, --session = my_spa_automation_session | etc.")
		print("PASSWORD")
		print("    Browser extension setup and unlock password")
		print(f"    Default: {self.password}")
		print("    -p, --password = my_password | etc.")
		print("TEST")
		print("    Test to run")
		print(f"    Default: {self.tests[0]}")
		print(f"    -t, --test = {(' | ').join(self.tests)}")
		print("VALUE")
		print("    Pass an extra value to a specific test")
		print("    Tests:")
		print("        existing:           pass a mnemonic")
		print("        unlock:             pass a [wrong] password")
		print("        unlock_brute_force: pass a wordlist")
		print("        access_control:     pass a lock state")
		print("    -v, --value = \"w1 w2 ... w12\" | WrongPassword123! | wordlist.txt | locked | unlocked | etc.")
		print("WAIT")
		print("    Wait time between browser actions")
		print(f"    Default: {self.wait}")
		print(f"    -w, --wait = {self.wait} | etc.")
		print("DEVELOPMENT")
		print("    Switch the internal script settings to the development environment")
		print("    -d, --dev")
		print("PROXY")
		print("    Web proxy to use")
		print("    -x, --proxy = http://127.0.0.1:8080")
		print("HELP")
		print("    Display this help message")
		print("    -h, --help")

if __name__ == "__main__":
	parser = MyParser(usage = None)
	parser.add_argument("-b", "--browser" , required = False, type   = str         , default = parser.browsers[0], choices = parser.browsers)
	parser.add_argument("-s", "--session" , required = False, type   = str         , default = ""                                           )
	parser.add_argument("-p", "--password", required = False, type   = str         , default = parser.password                              )
	parser.add_argument("-t", "--test"    , required = False, type   = str         , default = parser.tests[0]   , choices = parser.tests   )
	parser.add_argument("-v", "--value"   , required = False, type   = str         , default = ""                                           )
	parser.add_argument("-w", "--wait"    , required = False, type   = int         , default = parser.wait                                  )
	parser.add_argument("-d", "--dev"     , required = False, action = "store_true", default = False                                        )
	parser.add_argument("-x", "--proxy"   , required = False, type   = str         , default = ""                                           )
	args = parser.parse_args()
	# ------------------------------------
	test = Test(
		browser  = args.browser,
		session  = args.session,
		password = args.password,
		test     = args.test,
		value    = args.value,
		wait     = args.wait,
		dev      = args.dev,
		proxy    = args.proxy
	)
	test.run()
