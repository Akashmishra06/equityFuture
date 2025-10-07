cd "/root/equityFuture/renko_equity"
/usr/local/bin/pm2 start "timee.py" --interpreter="/root/akashResearchAndDevelopment/..venv/bin/python3" --name="timee-1-1" --no-autorestart --time


cd "/root/equityFuture/renko_equity"
/usr/local/bin/pm2 start "raise.py" --interpreter="/root/akashResearchAndDevelopment/..venv/bin/python3" --name="raise-1-1" --no-autorestart --time