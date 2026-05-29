"""
core/models.py — Modèles métier ConfirmaPay

Analogies Delphi/WinDev :
  Model Django       = Table BDD + DataSet (règles métier intégrées)
  ForeignKey         = Relation maître/détail avec intégrité référentielle
  Migrations         = Scripts DDL générés automatiquement depuis les classes
  Meta.ordering      = ORDER BY par défaut de la table
  save()             = événement OnBeforePost de WinDev / BeforePost de Delphi
  __str__            = ce qui s'affiche dans les listes déroulantes et l'admin
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.text import slugify
from datetime import date


# =============================================================================
# 1. USER MANAGER — Fabriqué sur mesure pour create_user / create_superuser
#
# Pourquoi en a-t-on besoin ?
# Le manager par défaut de Django attend un champ 'username'.
# On le remplace pour qu'il attende un 'email' à la place.
# En WinDev : c'est comme réécrire la procédure d'insertion dans votre
# gestionnaire de connexion pour accepter un email au lieu d'un login.
# =============================================================================

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")
        # normalize_email met le domaine en minuscules (Jean@GMAIL.COM → Jean@gmail.com)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hache le mot de passe en bcrypt — JAMAIS en clair
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        # setdefault : "mets True seulement si la clé n'est pas déjà fournie"
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


# =============================================================================
# 2. USER — Modèle d'authentification personnalisé
#
# AbstractUser hérite lui-même d'AbstractBaseUser + PermissionsMixin.
# Il apporte : password, is_active, is_staff, is_superuser, last_login,
#              date_joined, groups, user_permissions.
# On y ajoute nos champs et on supprime ceux qu'on ne veut pas.
#
# Règle d'or Django : définissez votre User custom DÈS LE DÉBUT du projet.
# Le changer après la première migration est un cauchemar (cf. docs Django).
# =============================================================================

class User(AbstractUser):

    # Neutraliser les champs hérités qu'on ne veut pas
    # "= None" sur un champ Django dans une sous-classe = suppression du champ
    username   = None  # On remplace par email comme identifiant
    first_name = None  # On utilise full_name à la place
    last_name  = None

    email = models.EmailField(
        unique=True,          # Contrainte UNIQUE en base
        verbose_name="Adresse email"
    )
    full_name = models.CharField(
        max_length=150,
        verbose_name="Nom complet"
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,    # INSERT seulement — jamais modifié ensuite
        verbose_name="Date de création"
    )

    # Dire à Django quel champ joue le rôle de "login"
    USERNAME_FIELD  = 'email'
    # Champs supplémentaires demandés par la commande createsuperuser
    REQUIRED_FIELDS = ['full_name']

    # Brancher notre manager personnalisé
    objects = UserManager()

    class Meta:
        verbose_name          = "Utilisateur"
        verbose_name_plural   = "Utilisateurs"
        ordering              = ['full_name']

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


# =============================================================================
# 3. BOUTIQUE — Le "tenant" (locataire) du SaaS multi-boutiques
#
# En architecture SaaS multi-tenant, chaque client (e-commerçant) est isolé
# dans sa Boutique. Toutes les données métier lui sont rattachées.
# En WinDev : votre table "Société" ou "Client SaaS" dans un ERP multi-sites.
# =============================================================================

class Boutique(models.Model):

    LANGUE_CHOICES = [
        ('fr',    'Français'),
        ('ar',    'Arabe'),
        ('ar_fr', 'Arabe + Français'),
    ]

    nom = models.CharField(
        max_length=200,
        verbose_name="Nom de la boutique"
    )
    # SlugField : version URL-safe du nom ("Ma Boutique" → "ma-boutique")
    # Utilisé dans les URLs propres (/boutique/ma-boutique/)
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,           # Généré automatiquement dans save()
        verbose_name="Slug URL"
    )
    logo = models.ImageField(
        upload_to='logos/',   # Stocké dans MEDIA_ROOT/logos/
        null=True,            # NULL autorisé en base
        blank=True,           # Champ optionnel dans les formulaires
        verbose_name="Logo"
    )
    langue_defaut = models.CharField(
        max_length=5,
        choices=LANGUE_CHOICES,
        default='ar_fr',
        verbose_name="Langue par défaut"
    )
    whatsapp_numero = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numéro WhatsApp principal"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        verbose_name        = "Boutique"
        verbose_name_plural = "Boutiques"
        ordering            = ['nom']

    def save(self, *args, **kwargs):
        # Auto-génération du slug à la création (si non fourni)
        # Gestion des collisions : "ma-boutique", "ma-boutique-2", etc.
        if not self.slug:
            base_slug = slugify(self.nom)
            slug, n = base_slug, 1
            while Boutique.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


# =============================================================================
# 4. MEMBERSHIP — Table de liaison User ↔ Boutique avec rôle
#
# Pattern "through table" : une relation N:N enrichie d'attributs.
# En Delphi/WinDev : table de jonction avec champs supplémentaires,
# type "BoutiqueUtilisateurs(IdBoutique, IdUtilisateur, Role, DateAjout)".
#
# Permet : un user peut être proprio d'une boutique et employé d'une autre.
# =============================================================================

class Membership(models.Model):

    ROLE_CHOICES = [
        ('proprietaire', 'Propriétaire'),
        ('employe',      'Employé'),
    ]

    # ForeignKey : côté "plusieurs" de la relation 1:N
    # on_delete=CASCADE : si le User est supprimé, ses Memberships le sont aussi
    # related_name : nom de l'accesseur inverse
    #   → user.memberships.all()     = toutes les boutiques de cet utilisateur
    #   → boutique.memberships.all() = tous les membres de cette boutique
    user = models.ForeignKey(
        'User',           # Guillemets = référence paresseuse (lazy) au modèle
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name="Utilisateur"
    )
    boutique = models.ForeignKey(
        Boutique,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name="Boutique"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='employe',
        verbose_name="Rôle"
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Membership"
        verbose_name_plural = "Memberships"
        # unique_together : contrainte d'unicité composite
        # = CREATE UNIQUE INDEX ON membership(user_id, boutique_id)
        # Un user ne peut avoir qu'UN seul rôle par boutique.
        unique_together = ('user', 'boutique')
        ordering        = ['boutique', 'role']

    def __str__(self):
        return f"{self.user.full_name} → {self.boutique} ({self.get_role_display()})"


# =============================================================================
# 5. CLIENT — Client d'une boutique, identifié par son numéro WhatsApp
#
# En WinDev : table Clients avec FK vers Societe, clé métier = numéro de tel.
# La contrainte unique_together empêche un doublon de numéro par boutique.
# =============================================================================

class Client(models.Model):

    boutique = models.ForeignKey(
        Boutique,
        on_delete=models.CASCADE,    # Boutique supprimée → ses clients supprimés
        related_name='clients',      # boutique.clients.all()
        verbose_name="Boutique"
    )
    whatsapp_numero = models.CharField(
        max_length=20,
        verbose_name="Numéro WhatsApp",
        # Format attendu : +212XXXXXXXXX
        # La validation du format se fait au niveau formulaire/serializer,
        # pas ici — les models ne valident que la structure BDD.
    )
    nom_complet   = models.CharField(max_length=200, verbose_name="Nom complet")
    adresse       = models.TextField(blank=True, verbose_name="Adresse")
    ville         = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    notes         = models.TextField(blank=True, verbose_name="Notes internes")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Client"
        verbose_name_plural = "Clients"
        unique_together     = ('boutique', 'whatsapp_numero')
        ordering            = ['nom_complet']

    def __str__(self):
        return f"{self.nom_complet} ({self.whatsapp_numero})"


# =============================================================================
# 6. COMMANDE — Cœur du système COD
#
# Deux FK de natures différentes :
#   boutique → CASCADE  : on peut purger une boutique et tout son historique
#   client   → PROTECT  : Django REFUSERA de supprimer un client qui a des
#                         commandes (lève ProtectedError). Sécurité données.
#
# En WinDev : table Commandes avec relation maître/détail vers LignesCommande.
# =============================================================================

class Commande(models.Model):

    STATUT_CHOICES = [
        ('en_attente',        'En attente'),
        ('confirmee',         'Confirmée'),
        ('annulee',           'Annulée'),
        ('sans_reponse',      'Sans réponse'),
        ('injoignable',       'Injoignable'),
        ('expediee',          'Expédiée'),
        ('livree',            'Livrée'),
        ('refusee_livraison', 'Refusée à la livraison'),
    ]

    boutique = models.ForeignKey(
        Boutique,
        on_delete=models.CASCADE,
        related_name='commandes',
        verbose_name="Boutique"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,    # Interdit la suppression d'un client actif
        related_name='commandes',    # client.commandes.all()
        verbose_name="Client"
    )
    numero_commande = models.CharField(
        max_length=30,
        verbose_name="Numéro de commande",
        # Généré automatiquement dans save() : format CMD-YYYYMM-XXXX
        # Unique par boutique (pas globalement), cf. unique_together ci-dessous
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente',
        verbose_name="Statut"
    )
    frais_livraison = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        verbose_name="Frais de livraison (MAD)"
    )
    montant_total = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Montant total (MAD)"
    )
    notes         = models.TextField(blank=True, verbose_name="Notes")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj      = models.DateTimeField(
        auto_now=True,               # Mis à jour automatiquement à chaque save()
        verbose_name="Dernière modification"
    )

    class Meta:
        verbose_name        = "Commande"
        verbose_name_plural = "Commandes"
        # Le numéro est unique PAR boutique : deux boutiques peuvent avoir CMD-202506-0001
        unique_together = ('boutique', 'numero_commande')
        ordering        = ['-date_creation']    # Les plus récentes en premier

    def save(self, *args, **kwargs):
        # Génération du numéro uniquement à la création (pk absent = nouvelle ligne)
        if not self.pk and not self.numero_commande:
            self.numero_commande = self._generer_numero()
        super().save(*args, **kwargs)

    def _generer_numero(self):
        """
        Séquence mensuelle par boutique : CMD-YYYYMM-XXXX
        Ex : CMD-202506-0001, CMD-202506-0002…
        Limite connue : pas atomic → collision possible sous très haute charge.
        Pour un volume e-commerce standard marocain, c'est amplement suffisant.
        """
        prefix = f"CMD-{date.today().strftime('%Y%m')}"
        derniere = (
            Commande.objects
            .filter(boutique=self.boutique, numero_commande__startswith=prefix)
            .order_by('-numero_commande')
            .first()
        )
        seq = 1
        if derniere:
            try:
                seq = int(derniere.numero_commande.split('-')[-1]) + 1
            except (ValueError, IndexError):
                pass
        return f"{prefix}-{seq:04d}"

    def __str__(self):
        return f"{self.numero_commande} — {self.client.nom_complet} [{self.get_statut_display()}]"


# =============================================================================
# 7. LIGNE COMMANDE — Détail produit d'une commande
#
# Relation maître/détail classique.
# related_name='lignes' → commande.lignes.all() = tous les produits de la commande
# =============================================================================

class LigneCommande(models.Model):

    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name='lignes',       # commande.lignes.all()
        verbose_name="Commande"
    )
    nom_produit   = models.CharField(max_length=300, verbose_name="Nom du produit")
    quantite      = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    prix_unitaire = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Prix unitaire (MAD)"
    )

    class Meta:
        verbose_name        = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"

    @property
    def sous_total(self):
        # @property = champ calculé, pas stocké en base (comme une formule de colonne)
        return self.quantite * self.prix_unitaire

    def __str__(self):
        return f"{self.nom_produit} × {self.quantite} → {self.sous_total} MAD"


# =============================================================================
# 8. TEMPLATE — Modèles de messages WhatsApp réutilisables
#
# Note de nommage : "Template" est aussi une classe dans django.template.
# Dans ce fichier c'est sans ambiguïté. Si vous importez les deux dans
# un même fichier, utilisez : from core.models import Template as TemplateMsg
# =============================================================================

class Template(models.Model):

    TYPE_CHOICES = [
        ('confirmation', 'Confirmation de commande'),
        ('relance',      'Relance sans réponse'),
        ('expedition',   "Avis d'expédition"),
        ('autre',        'Autre'),
    ]

    boutique = models.ForeignKey(
        Boutique,
        on_delete=models.CASCADE,
        related_name='templates',    # boutique.templates.all()
        verbose_name="Boutique"
    )
    nom  = models.CharField(max_length=200, verbose_name="Nom du template")
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name="Type de message"
    )
    contenu_fr = models.TextField(
        verbose_name="Contenu en français",
        help_text="Variables : {nom_client}  {numero_commande}  {montant}"
    )
    contenu_ar = models.TextField(
        verbose_name="Contenu en arabe",
        help_text="المتغيرات : {nom_client}  {numero_commande}  {montant}"
    )
    actif         = models.BooleanField(default=True, verbose_name="Actif")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Template de message"
        verbose_name_plural = "Templates de messages"
        ordering            = ['boutique', 'type', 'nom']

    def __str__(self):
        return f"[{self.get_type_display()}] {self.nom} ({self.boutique})"


# =============================================================================
# 9. MESSAGE — Historique de tous les messages WhatsApp envoyés
#
# Deux FK de comportements différents :
#   commande → CASCADE  : si la commande est supprimée, ses messages le sont
#   template → SET_NULL : si le template est supprimé, le message est conservé
#                         (l'historique reste intact, template mis à NULL)
# =============================================================================

class Message(models.Model):

    STATUT_ENVOI_CHOICES = [
        ('en_attente', "En attente d'envoi"),
        ('envoye',     'Envoyé'),
        ('echec',      "Échec d'envoi"),
        ('livre',      'Livré (WhatsApp confirmé)'),
        ('lu',         'Lu par le destinataire'),
    ]

    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name='messages',     # commande.messages.all()
        verbose_name="Commande"
    )
    template = models.ForeignKey(
        Template,
        on_delete=models.SET_NULL,   # Template supprimé → champ mis à NULL
        null=True,
        blank=True,
        related_name='messages_envoyes',
        verbose_name="Template utilisé"
    )
    contenu_envoye = models.TextField(verbose_name="Contenu envoyé")
    statut_envoi   = models.CharField(
        max_length=15,
        choices=STATUT_ENVOI_CHOICES,
        default='en_attente',
        verbose_name="Statut d'envoi"
    )
    reponse_recue = models.TextField(blank=True, verbose_name="Réponse du client")
    date_envoi    = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")
    date_reponse  = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Date de la réponse"
    )

    class Meta:
        verbose_name        = "Message"
        verbose_name_plural = "Messages"
        ordering            = ['-date_envoi']

    def __str__(self):
        return f"[{self.get_statut_envoi_display()}] {self.commande.numero_commande}"
