import time
import subprocess

# File paths
file_to_check = "/root/equityFuture/renko_equity/check.txt"
file_to_write = "/root/equityFuture/renko_equity/index.txt"

stocks = [
    # "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "AMBUJACEM", "APOLLOHOSP",
    # "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND",
    # "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON",
    "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA",
    "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DEEPAKNTR", "DIVISLAB", "DIXON",
    "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GNFC", "GODREJCP",
    "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCLIFE", "HEROMOTOCO",
    "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "IGL",
    "INDHOTEL", "INDIACEM", "INDIGO", "INDUSINDBK", "INFY", "IOC", "IPCALAB", "ITC", "JINDALSTEL", "JKCEMENT",
    "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTTS", "LUPIN", "MANAPPURAM", "MARICO",
    "MARUTI", "MCX", "MFSL", "MGL", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NESTLEIND",
    "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET", "PFC",
    "PIDILITIND", "PIIND", "PNB", "POWERGRID", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBILIFE",
    "SBIN", "SHREECEM", "SIEMENS", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS",
    "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL",
    "VEDL", "VOLTAS", "WIPRO"
]

write_count = 0  # Counter for how many times we've written
stock_index = 0  # Index for current stock

while stock_index < len(stocks):
    try:
        with open(file_to_check, "r") as f:
            content = f.read().strip().lower()

        if "yes" in content:
            # Both values are the same current stock
            value = stocks[stock_index]

            # Write the same stock twice
            with open(file_to_write, "w") as f2:
                f2.write(f"{value}\n{value}\n")

            write_count += 1
            print(f"[{write_count}] 'yes' found! Written '{value}' in both lines to {file_to_write}")

            # Clear file1
            with open(file_to_check, "w") as f1:
                f1.write("")

            # import subprocess
            # bash_file = "bash.sh"  # replace with full path if needed
            # try:
            #     # Run bash script
            #     subprocess.run(["bash", bash_file], check=True)
            #     print(f"{bash_file} executed successfully.")
            # except subprocess.CalledProcessError as e:
            #     print(f"Error running {bash_file}: {e}")

            # Move to next stock for next "yes"
            stock_index += 1
        else:
            print(f"'yes' not found. Checking again in 30 seconds...")

    except FileNotFoundError:
        print(f"{file_to_check} not found. Checking again in 30 seconds...")

    time.sleep(30)

    import subprocess
    bash_file = "bash.sh"  # replace with full path if needed
    try:
        # Run bash script
        subprocess.run(["bash", bash_file], check=True)
        print(f"{bash_file} executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running {bash_file}: {e}")