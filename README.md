# project-whistlebot
a prototype reporting interface for discord moderation 
capstone project for [ada developers academy, cohort 14](https://adadevelopersacademy.org/)

## what is project whistlebot? 
project whistlebot is an experiment to explore a possible reporting system/web interface (whistlebot) that moderators and admins can use to ensure the safety and comfort of members of their community. as such, while whistlebot will be designed a built with the best possible experience in mind, it will also be built with the intent of trying things that might not work as well in practice, trying new things and seeing how they work, and learning from all that to help improve the way we can moderate our communities. 

## what technologies does whistlebot use? 
- python
   - [hikari](https://github.com/hikari-py/hikari)
   - [hikari-lightbulb](https://github.com/tandemdude/hikari-lightbulb)
- quart
   - [quart-discord](https://github.com/jnawk/Quart-Discord) (TO BE REMOVED)
- mongodb
   - pymongo

## what if i decide to use whistlebot? 
whistlebot will be planned to anticipate the worst, but assume the best -- that means that while there will (hopefully) be safeguards from using whistlebot's data with malicious intent, at this point in time, project whistlebot cannot be held responsible for misuse of its critical features in moderating servers, but will have some features included to help prevent members who may try to abuse the system.

### installation 
#### pre-requisites
this project is currently set up to be run locally or on an Amazon EC2 machine (not recommended for security reasons).

at minimum, it is assumed that you have:
- [the most recent version of python installed on your machine](https://www.python.org/downloads/)
- a mongoDB uri from mongoDB's cloud. [here's a good guide.](https://www.knowi.com/blog/getting-started-with-mongodb-atlas-overview-and-tutorial/)
- a discord bot. [see the section **How to Create a Discord Bot Account** here.]()
   - go to OAuth2 here: https://discord.com/developers/applications/<YOUR_DISCORD_BOT>/oauth2
      - add <EC2 MACHINE Public IPv4 DNS>/callback (for AWS EC2 Ubuntu 20.04) or http://0.0.0.0:8000/callback to your redirects. 
   - go to /bot here: https://discord.com/developers/applications/<YOUR_DISCORD_BOT>/bot
      - turn on ALL options EXCEPT **Requires OAuth2 Code Grant**.
      - under **Bot Permissions**, turn on ALL permissions under **General Permissions** and **Text Permissions** EXCEPT: _administrator, create instant invite, change nickname, manage emojis, send TTS messages, attach files, mention everyone, use external emojis_
- a means to run a python virtual environment (if you don't wish to deploy on AWS) OR an AWS EC2 virtual machine (Ubuntu 20.04) with an Elastic IP.
   - **if you are running this on AWS EC2 Ubuntu 20.04:**
      - go to **Security Groups** to make sure that your **Inbound rules** are "anywhere" for the following ports: 80 (HTTP), 8080, 8000, 443 (HTTPS). you may set your SSH rule so that only your IP address can use port 22.
      - verify that you have an IAM user with all Admin privileges associated with your machine.
      - make sure you have an Elastic IP associated with your machine. scroll down to **Adding Elastic IP addresses** [here](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html). 
      - i recommend [Cyberduck](https://cyberduck.io/) for managing files, connections, and terminals on your EC2 machine.
      - **gunner bones on youtube** has an incredibly helpful setup tutorial [here.](https://www.youtube.com/watch?v=YiieNfjE9qo&t=890s)
   - **if you are running this on your machine:**
      - make sure you have a virtual environment for python, like [pyenv](https://github.com/pyenv/pyenv)
      - otherwise (for the very lazy), [you can install PyCharm for free.](https://www.jetbrains.com/pycharm/download/)  

#### setup 
1. open your terminal (or connect to your EC2 terminal if you are running this on EC2) and clone this repo. 
2. run `$ pip install -r requirements.txt` to download dependencies.
3. create a .env file in the root folder **/project-whistlebot/** -- to find what environmental variables you will need, open the settings.py file at **/project-whistlebot/app** , which in the comments will explain to you which variables are needed to set up your env file. 

#### running whistlebot
##### if you are running this on AWS EC2 Ubuntu 20.04
1. `cd` into `project-whistlebot/app.`
2. run the following commands: 
  - `$ ./ubuntu_nrun.sh`
  - `$ ./ubuntu_apprun.sh`
  - the terminal should output something about nohup per command, and you can press the enter key to bypass.  
3. close terminal. your bot should be running and your site will be up at your EC2 machine public IPv4 DNS.
4. to kill your processes, type `$ ps aux` and look for the PID for `python3 bot.py` and `/usr/bin/python3...`. type `$ kill <PID>` for each process to terminate.    

##### if you are running this on your machine (terminal)
1. `cd` into `project-whistlebot/app.`
2. in the root folder, open two new terminals. 
3. in one terminal, enter `$ ./ubuntu_nrun.sh` for the bot.
4. in another terminal, enter `$ ./ubuntu_apprun.sh` for the site, which should be up at http://0.0.0.0:8000/.
5. you may close these terminals if you no longer wish to run them. 

##### if you are running this on PyCharm
1. open project in pycharm. run bot.py and app.py. make sure they are both configured to the project-whistlebot root folder to collect env variables. 

## can i contribute to whistlebot?
__AS OF FEB 12, 2021 --__ whistlebot is currently a capstone project for the classroom portion of cohort 14 of [ada developers academy](https://adadevelopersacademy.org/). 

please be noted that although a front end was created for purposes of the capstone, **it is highly likely that project-whistlebot will no longer have a dashboard/interface in future versions** in order to better streamline with how discord moderators typically run servers.

starting around march, i will be open to reviewing pull requests and suggested modifications for the bot, but cannot guarantee the speediest response until possibly summer 2021! thank you for understanding! 

## where can i check whistlebot's progress/intended features?
you can view the trello board **[HERE](https://trello.com/b/pRWqDbYP/project-whistlebot)**.

for very rough wireframes, please see the wireframes folder!

