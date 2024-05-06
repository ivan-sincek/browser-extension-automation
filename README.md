# Browser Extension Automation

Run a browser extension in a sandboxed web browser, completely isolated from your main / daily web browser, and without any fear of corrupting or loosing your real data.

Whom is this script intended for?

* Software engineers for unit testing purposes.
* Quality assurance engineers for quality control purposes.
* Product owners for demonstration purposes.
* Cybersecurity engineers for security testing purposes.

For demonstration purposes, this script is based on [MetaMask](https://chromewebstore.google.com/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn) (v11.13.1) browser extension for Chrome web browser, but can easily be modified to suit all of your needs.

__As of this writing, Playwright only supports Chromium browser extensions.__

Tested on:

* macOS Sonoma 14.0
* Windows 10 Pro and Windows 11 Pro
* Kali Linux 2024.1 (Debian)

Made for educational purposes. I hope it will help!

Future plans:

* add more security related flows.

## Table of Contents

* [How to Run](#how-to-run)
    * [Environment Setup](#environment-setup)
    * [Manually Load a Browser Extension](#manually-load-a-browser-extension)
* [For Developers](#for-developers)
* [Usage](#usage)
* [Images](#images)

## How to Run

Open your preferred console from [/src/](https://github.com/ivan-sincek/browser-extension-automation/tree/main/src) and run the commands shown below.

Install required packages:

```fundamental
pip3 install -r requirements.txt
```

Install Chromium web browser:

```fundamental
playwright install chromium
```

Make sure each time you upgrade your Playwright dependency to re-install Chromium web browser.

Install [MetaMask](https://chromewebstore.google.com/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn) to your main / daily web browser.

Run the script:

```fundamental
python3 automation.py
```

### Environment Setup

To set up a sandboxed environment, run:

```fundamental
python3 automation.py -s my_automation_session
```

If `-s` option is not specified, a new random user session directory will be created in your current working directory; otherwise, do the setup in your desired directory.

If `-e` option is not specified, the script will try to locate, copy, and load the copied browser extension for you based on the identifier; otherwise, do the same from the directory you specified.

If `-t` option is not specified, the script will open a web browser and only load the browser extension.

__To continue using the same browser session, simply run the above command again.__

__If you wish to update your browser extension, then, inside your `my_automation_session` directory, delete the `browser_extension` directory and simply run the above command again.__

If a browser extension already exists in your user session directory, you will be prompted to overwrite it.

## Manually Load a Browser Extension

Unpack your desired Chrome browser extension, then, load the `dist` directory:

```fundamental
python3 automation.py -s my_automation_session -e dist --dev
```

__To switch the internal script settings to the development environment, add `--dev` option.__

## For Developers

* [Generic Building Blocks \(Single Action\)](https://github.com/ivan-sincek/browser-extension-automation/blob/main/src/automation.py#L279)
* [Generic Building Blocks \(Multiple Actions\)](https://github.com/ivan-sincek/browser-extension-automation/blob/main/src/automation.py#L355)
* [Webhook Building Blocks \(Collaborator Server / Email Service\)](https://github.com/ivan-sincek/browser-extension-automation/blob/main/src/automation.py#L395)
* [MetaMask Flows](https://github.com/ivan-sincek/browser-extension-automation/blob/main/src/automation.py#L447)

Follow the comments inside the source code for more information.

## Usage

```fundamental
Automation v1.1 ( https://github.com/ivan-sincek/browser-extension-automation )

Usage: python3 automation.py [-b browser] [-s session] [-e extension] [-i identifier] [-p password] [-t test] [-v value] [-w wait] [--dev] [-x proxy]

DESCRIPTION
    Browser extension automation script
BROWSER
    Browser to run
    Default: chromium
    -b, --browser = chromium
SESSION
    User session directory
    Default: random
    -s, --session = my_automation_session | etc.
EXTENSION
    Browser extension directory
    Default: auto-located based on the identifier
    -e, --extension = dist | "/Users/john.doe/Library/Application Support/Google/Chrome/Default/Extensions/nkbihfbeogaeaoehlefnkodbefgpgknn/11.13.1_0" | etc.
IDENTIFIER
    Browser extension identifier
    Default: nkbihfbeogaeaoehlefnkodbefgpgknn
    -i, --identifier = nkbihfbeogaeaoehlefnkodbefgpgknn | etc.
PASSWORD
    Browser extension setup and unlock password
    Default: Password123!
    -p, --password = my_password | etc.
TEST
    Test to run
    Default: open
    -t, --test = open | create | existing | unlock | brute_force_unlock | idle_lock | access_control
VALUE
    Pass an extra value to a specific test
    Tests:
        existing:           pass a mnemonic
        unlock:             pass a [wrong] password
        unlock_brute_force: pass a wordlist
        access_control:     pass a lock state
    -v, --value = "w1 w2 ... w12" | WrongPassword123! | wordlist.txt | locked | unlocked | etc.
WAIT
    Wait time between browser actions
    Default: 2
    -w, --wait = 2 | etc.
DEVELOPMENT
    Switch the internal script settings to the development environment
    -d, --dev
PROXY
    Web proxy to use
    -x, --proxy = http://127.0.0.1:8080
HELP
    Display this help message
    -h, --help
```

## Images

<p align="center"><img src="https://github.com/ivan-sincek/browser-extension-automation/blob/main/img/metamask_create_wallet.jpg" alt="MetaMask Create Wallet"></p>

<p align="center">Figure 1 - MetaMask Create Wallet</p>

<p align="center"><img src="https://github.com/ivan-sincek/browser-extension-automation/blob/main/img/metamask_access_control_locked.jpg" alt="MetaMask Access Control (Locked)"></p>

<p align="center">Figure 2 - MetaMask Access Control (Locked)</p>
