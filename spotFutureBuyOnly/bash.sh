cd "/root/equityFuture/spotFutureBuyOnly"
/usr/local/bin/pm2 start "spotFutureBuyOnly_40_with_ema_slope.py" --interpreter="/root/akashResearchAndDevelopment/..venv/bin/python3" --name="spotFutureBuyOnly_40_with_ema_slope-1-1" --no-autorestart --time


cd "/root/equityFuture/spotFutureBuyOnly"
/usr/local/bin/pm2 start "spotFutureBuyOnly_40_with_trailing.py" --interpreter="/root/akashResearchAndDevelopment/..venv/bin/python3" --name="spotFutureBuyOnly_40_with_trailing-1-1" --no-autorestart --time


cd "/root/equityFuture/spotFutureBuyOnly"
/usr/local/bin/pm2 start "spotFutureBuyOnly_40.py" --interpreter="/root/akashResearchAndDevelopment/..venv/bin/python3" --name="spotFutureBuyOnly_40-1-1" --no-autorestart --time