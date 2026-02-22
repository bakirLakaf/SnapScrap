import os
from flask import Blueprint, request, jsonify, redirect, url_for, render_template, current_app
from flask_login import current_user, login_required
from webapp.models import db, User

try:
    import stripe
except ImportError:
    stripe = None

billing_bp = Blueprint("billing", __name__)

# Try to get Stripe keys from environment variables
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

if stripe:
    stripe.api_key = STRIPE_SECRET_KEY

# Pricing IDs (you will replace these with the actual Price IDs from your Stripe Dashboard)
PRICES = {
    "pro": os.environ.get("STRIPE_PRICE_PRO", "price_H5bXXXXX"),
    "enterprise": os.environ.get("STRIPE_PRICE_ENTERPRISE", "price_H5bYYYYY")
}

@billing_bp.route("/api/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    if not stripe:
        return jsonify({"error": "Stripe library is not installed (pip install stripe)"}), 500
        
    data = request.get_json() or {}
    tier = data.get("tier", "pro")
    
    price_id = PRICES.get(tier)
    
    if not price_id:
        return jsonify({"error": "Invalid subscription tier selected."}), 400
        
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=request.host_url + "billing/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.host_url + "billing/cancel",
            client_reference_id=str(current_user.id),
            metadata={
                "user_id": current_user.id,
                "tier": tier
            }
        )
        return jsonify({"checkout_url": checkout_session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 403

@billing_bp.route("/billing/success")
@login_required
def success():
    # Stripe redirects here after successful payment
    session_id = request.args.get("session_id")
    if session_id and stripe:
        try:
            # Optionally verify the session directly with Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                # We can update the db here, but it's better to rely on Webhooks
                pass
        except Exception:
            pass
            
    return render_template("billing_success.html")

@billing_bp.route("/billing/cancel")
@login_required
def cancel():
    return render_template("billing_cancel.html")

@billing_bp.route("/api/webhook", methods=["POST"])
def stripe_webhook():
    if not stripe:
        return "Stripe not configured", 500
        
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return "Invalid signature", 400

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Retrieve the user id from client_reference_id
        user_id = session.get("client_reference_id")
        customer_id = session.get("customer")
        tier = session.get("metadata", {}).get("tier", "pro")
        
        if user_id:
            user = User.query.get(int(user_id))
            if user:
                user.subscription_tier = tier
                user.stripe_customer_id = customer_id
                db.session.commit()
                current_app.logger.info(f"User {user_id} upgraded to {tier} tier.")
                
    elif event["type"] == "customer.subscription.deleted":
        # Handle subscription cancellation
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.subscription_tier = "free"
            db.session.commit()
            current_app.logger.info(f"User {user.id} subscription canceled. Downgraded to free.")

    return jsonify({"status": "success"})
