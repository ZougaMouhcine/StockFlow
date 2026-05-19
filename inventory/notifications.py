import base64
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def build_order_message(order, items):
	items_summary = ", ".join(
		f"{item['quantity']}x {item['product'].name}" for item in items
	)
	if not items_summary:
		items_summary = "Aucun article"

	created_at = timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M")

	message = (
		"Nouvelle commande recue.\n"
		f"Commande: #{order.pk}\n"
		f"Client: {order.full_name}\n"
		f"Telephone: {order.phone}\n"
		f"Adresse: {order.address}, {order.city}\n"
		f"Produits: {items_summary}\n"
		f"Total: {order.total_amount} MAD\n"
		"Paiement: non specifie\n"
		f"Date: {created_at}"
	)
	return message


def _send_meta_whatsapp_message(to_number, body):
	token = settings.WHATSAPP_TOKEN
	phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
	if not token or not phone_number_id:
		logger.warning("WhatsApp Meta API not configured; skipping notification.")
		return False

	url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
	payload = {
		"messaging_product": "whatsapp",
		"to": to_number,
		"type": "text",
		"text": {"body": body},
	}
	data = json.dumps(payload).encode("utf-8")
	request = urllib.request.Request(
		url,
		data=data,
		headers={
			"Authorization": f"Bearer {token}",
			"Content-Type": "application/json",
		},
	)

	try:
		with urllib.request.urlopen(request, timeout=10) as response:
			response.read()
		return True
	except Exception:
		logger.exception("WhatsApp Meta API notification failed.")
		return False


def _send_twilio_whatsapp_message(to_number, body):
	account_sid = settings.TWILIO_ACCOUNT_SID
	auth_token = settings.TWILIO_AUTH_TOKEN
	from_number = settings.TWILIO_WHATSAPP_FROM
	if not account_sid or not auth_token or not from_number:
		logger.warning("Twilio WhatsApp not configured; skipping notification.")
		return False

	url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
	payload = urllib.parse.urlencode(
		{
			"From": f"whatsapp:{from_number}",
			"To": f"whatsapp:{to_number}",
			"Body": body,
		}
	).encode("utf-8")
	basic_auth = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
	request = urllib.request.Request(
		url,
		data=payload,
		headers={
			"Authorization": f"Basic {basic_auth}",
			"Content-Type": "application/x-www-form-urlencoded",
		},
	)

	try:
		with urllib.request.urlopen(request, timeout=10) as response:
			response.read()
		return True
	except Exception:
		logger.exception("Twilio WhatsApp notification failed.")
		return False


def send_admin_whatsapp_notification(order, items):
	if not settings.WHATSAPP_ENABLED:
		return False

	admin_number = settings.WHATSAPP_ADMIN_TO
	if not admin_number:
		logger.warning("WHATSAPP_ADMIN_TO is empty; skipping notification.")
		return False

	message = build_order_message(order, items)
	provider = settings.WHATSAPP_PROVIDER

	if provider == "twilio":
		return _send_twilio_whatsapp_message(admin_number, message)
	return _send_meta_whatsapp_message(admin_number, message)
