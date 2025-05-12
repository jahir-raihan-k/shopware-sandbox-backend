from decouple import config
from apideck_unify import Apideck, ConsumerMetadataTypedDict


class ApideckShopwareManager:
    UNIFIED_API = "ecommerce"
    SERVICE_ID = "shopware"

    def __init__(self, api_key: str, app_id: str, consumer_id: str):
        self.api_key = api_key
        self.app_id = app_id
        self.consumer_id = consumer_id

    def _client(self) -> Apideck:
        return Apideck(
            api_key=self.api_key,
            app_id=self.app_id,
            consumer_id=self.consumer_id,
        )

    def create_consumer(self, metadata: dict | None = None):
        """
        Create a new consumer to establish a connection with shopware.
        Args:
            metadata
        """

        # Set consumer meta data
        dic = ConsumerMetadataTypedDict()
        dic["account_name"] = metadata.get("account_name", "From Installation")
        dic["user_name"] = metadata.get("user_name", "From Installation")
        dic["email"] = metadata.get("email", "from_installation@gmail.com")
        dic["image"] = metadata.get("image", "https://www.spacex.com/static/images/share.jpg")

        # Create consumer
        with self._client() as apideck:
            res = apideck.vault.consumers.create(
                consumer_id=self.consumer_id,
                app_id=self.app_id,
                metadata=dic
            )
            assert res.create_consumer_response is not None

    def create_connection(self, client_id: str, client_secret: str, shop_url: str, scopes: list[str] | None = None):
        """
        Creates a connection between consumer and shopware.
        Args:
            client_id
            client_secret
            shop_url
            scopes
        """

        # Beside client-id, secret and shop_domain, I haven't tested what else is required out here :)
        token_url = f"{shop_url.rstrip('/')}/api/oauth/token"
        conn_config = {
            "client_id": client_id,
            "client_secret": client_secret,
            "token_url": token_url,
            "instance_url": shop_url,
            "shop_domain": shop_url.replace("https://", "")
        }

        # Create the connection
        with self._client() as c:
            resp = c.vault.connections.update(
                unified_api=self.UNIFIED_API,
                service_id=self.SERVICE_ID,
                settings=conn_config,
                enabled=True
            )
            return resp

    def authorize_connection(self):
        """
        After creating a connection between consumer and shopware, this method will
        authorize the connection.
        """

        with self._client() as c:
            return c.vault.connections.token(
                unified_api=self.UNIFIED_API,
                service_id=self.SERVICE_ID,
                consumer_id=self.consumer_id,
                app_id=self.app_id,
            )

    def list_products(self, limit: int = 50, updated_since: str | None = None) -> list[dict]:
        """
        Return a list of products to test if the connection is working.
        Will updated about what's this "updated_since" param doing here.
        Args:
            limit
            updated_since
        """

        all_products = []
        with self._client() as c:
            params = {"service_id": self.SERVICE_ID}
            if updated_since:
                params["pass_through"] = {"updated_since": updated_since}

            resp = c.ecommerce.products.list(limit=limit, **params)
            all_products.extend(resp.get_products_response.data)

            while getattr(resp, "next_cursor", None):
                resp = resp.next()
                all_products.extend(resp.get_products_response.data)

        return all_products


# ─────────── Main Entry ───────────

def main():
    api_key = config("APIDECK_API_KEY")
    app_id = config("APIDECK_APP_ID")
    consumer_id = "shopID as consumer Id" # Needs to be a valid unique id. Eg: ShopID or ShopUrl

    client_id = config("SHOPWARE_CLIENT_ID")
    client_secret = config("SHOPWARE_CLIENT_SECRET")
    shop_url = config("SHOPWARE_SHOP_URL")

    mgr = ApideckShopwareManager(api_key, app_id, consumer_id)

    # 1. Create consumer
    consumer_account_name = "Real request for data"
    consumer_user_name = ""
    consumer_email = ""
    consumer_image = ""
    mgr.create_consumer(metadata={
        "shopUrl": shop_url,
        "account_name": consumer_account_name,
        "user_name": consumer_user_name,
        "email": consumer_email,
        "image": consumer_image
    })

    # 2. Create connection
    mgr.create_connection(client_id, client_secret, shop_url)

    # 3. Authorize connection
    res = mgr.authorize_connection()
    assert res.get_connection_response is not None
    print("Authorized:", res.get_connection_response)

    # 4. Fetch test products
    products = mgr.list_products(limit=10)
    for p in products:
        print(p["id"], p["productNumber"], p["name"])


if __name__ == "__main__":
    main()
