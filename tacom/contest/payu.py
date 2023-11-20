import json
import requests

from django.conf import settings
from django.urls import reverse
from django.utils.translation import get_language

from .models import Payment

PAYU_URL = 'https://secure.snd.payu.com'
PAYU_OAUTH_ENDPOINT = '/pl/standard/user/oauth/authorize'
PAYU_ORDER_ENDPOINT = '/api/v2_1/orders'


def get_oauth_token():
    data = {
        'grant_type': 'client_credentials',
        'client_id': settings.PAYU_CLIENT_ID,
        'client_secret': settings.PAYU_CLIENT_SECRET
    }
    url = PAYU_URL + PAYU_OAUTH_ENDPOINT
    r = requests.post(url, data=data)
    return r.json().get('access_token')


def get_order_link(payment: Payment, token=None, ip='127.0.0.1', next_url=None, notify_url=None):
    if not token:
        token = get_oauth_token()
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "customerIp": ip,
        "continueUrl": next_url,
        "notifyUrl": notify_url,
        "merchantPosId": settings.PAYU_POS_ID,
        "description": "Konkurs",
        "currencyCode": payment.currency,
        "totalAmount": int(payment.amount * 100),
        "buyer": {
            "email": payment.user.email,
            "phone": payment.user.phone,
            "firstName": payment.user.first_name,
            "lastName": payment.user.last_name,
            "language": get_language()
        }
    }

    url = PAYU_URL + PAYU_ORDER_ENDPOINT
    print(json.dumps(data, indent=2))
    r = requests.post(url, headers=headers, json=data, allow_redirects=False)
    print(r.json())
    payment.code = r.json().get('orderId')
    payment.save()
    return r.json().get('redirectUri')
