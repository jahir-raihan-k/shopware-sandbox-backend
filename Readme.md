# This is a test backend for the shopware app extension we've built.

## Steps

1. Clone this repository
    ```bash
    git clone https://github.com/jahir-raihan-k/shopware-sandbox-backend.git
    ```
2. Create & activate virtual environment to isolate packages used
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```
3. Install all required packages
   ```bash
   pip install -r requirements.txt
   ```
4. Run
   ```bash
   fastapi dev main.py
   ```
   
### What about the `api_deck_shopware_test` file?

Well, that one I've created for testing the lifecycle from connecting a shop to 
pull out its data.

**Simplified script steps**
1. Crates a consumer
2. Creates a connection. [Shopware - Consumer]
3. Authorizes the connection
4. Fetches products data using unify api

If you want to run it also, create a `.env` file. Copy the variable names from `.env.templat` and place them appropriately.
Then hit the run button.

But to be able to run it, you'll need a shopware sandbox account. And from that sandbox account
client-id & client secret is required.

### Steps to obtain shopware sandbox account and it's credentials

1. **Follow this [documentation](https://docs.shopware.com/en/shopware-account-en/general/cloud-sandbox) to create a sandbox account**
2. After logging into the sandbox, navigate to `settings`  >  `system`  > `Integration` & click `Add integration` button in the top-right corner.
