cd ~/Projects/confirmapay
cat > README.md << 'EOF'
# ConfirmaPay

SaaS de confirmation de commandes COD (Cash on Delivery) par WhatsApp pour e-commerçants marocains.

ConfirmaPay automatise la confirmation des commandes en paiement à la livraison, un processus aujourd'hui géré manuellement par appels téléphoniques au Maroc, avec un taux d'échec élevé. L'objectif est de réduire ce taux d'échec en offrant aux clients un canal de confirmation simple et digne de confiance via WhatsApp.

## Stack technique

- **Backend** : Django (Python 3.12)
- **Base de données** : PostgreSQL 17
- **Frontend** : Tailwind CSS v4 + HTMX
- **Authentification** : Django custom User model (connexion par email)

## Architecture

Application multi-tenant : chaque **Boutique** est un tenant isolé. Les utilisateurs accèdent aux données via leur appartenance (Membership) à une ou plusieurs boutiques.

Modèles principaux : User, Boutique, Membership, Client, Commande, LigneCommande, Template, Message.

## Prérequis

- Python 3.12+
- PostgreSQL 17 avec une base nommée `confirmapay`
- pip

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/msstrategie/confirmapay.git
cd confirmapay

# Créer et activer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env   # puis adapter les valeurs

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Lancer le serveur de développement
python manage.py runserver
```

L'application est accessible sur http://127.0.0.1:8000
L'interface d'administration sur http://127.0.0.1:8000/admin

## État du projet

En développement actif.

- [x] Modélisation métier complète
- [x] Interface d'administration Django
- [ ] Authentification e-commerçant (front)
- [ ] Dashboard de gestion des commandes
- [ ] Page de confirmation client
- [ ] Intégration WhatsApp Business API

## Auteur

Mouhsin
