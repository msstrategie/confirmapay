from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Boutique, Membership, Client, Commande, LigneCommande, Template, Message


# ---------------------------------------------------------------------------
# USER — Adapter l'admin par défaut à notre User sans username
# BaseUserAdmin fourni par Django gère déjà les groupes et permissions.
# ---------------------------------------------------------------------------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering     = ('email',)
    list_display = ('email', 'full_name', 'is_staff', 'is_active', 'date_creation')
    search_fields = ('email', 'full_name')
    list_filter  = ('is_staff', 'is_superuser', 'is_active')

    # Formulaire d'édition d'un utilisateur existant
    fieldsets = (
        (None,                    {'fields': ('email', 'password')}),
        ('Informations',          {'fields': ('full_name',)}),
        ('Permissions',           {'fields': ('is_active', 'is_staff', 'is_superuser',
                                              'groups', 'user_permissions')}),
        ('Dates',                 {'fields': ('last_login', 'date_creation')}),
    )
    readonly_fields = ('date_creation', 'last_login')

    # Formulaire de création d'un nouvel utilisateur
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2'),
        }),
    )


# ---------------------------------------------------------------------------
# BOUTIQUE
# ---------------------------------------------------------------------------

@admin.register(Boutique)
class BoutiqueAdmin(admin.ModelAdmin):
    list_display  = ('nom', 'slug', 'langue_defaut', 'actif', 'date_creation')
    list_filter   = ('actif', 'langue_defaut')
    search_fields = ('nom',)
    prepopulated_fields = {'slug': ('nom',)}  # Génère le slug automatiquement dans l'admin


# ---------------------------------------------------------------------------
# MEMBERSHIP — affiché inline dans Boutique ET en liste autonome
# ---------------------------------------------------------------------------

class MembershipInline(admin.TabularInline):
    # TabularInline = sous-grille dans le formulaire parent
    # Équivalent d'un TDBGrid lié en maître/détail dans Delphi
    model  = Membership
    extra  = 1   # Nombre de lignes vides affichées par défaut
    fields = ('user', 'role', 'date_ajout')
    readonly_fields = ('date_ajout',)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display  = ('user', 'boutique', 'role', 'date_ajout')
    list_filter   = ('role',)
    search_fields = ('user__email', 'user__full_name', 'boutique__nom')


# ---------------------------------------------------------------------------
# CLIENT
# ---------------------------------------------------------------------------

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display  = ('nom_complet', 'whatsapp_numero', 'ville', 'boutique', 'date_creation')
    list_filter   = ('boutique', 'ville')
    search_fields = ('nom_complet', 'whatsapp_numero')


# ---------------------------------------------------------------------------
# COMMANDE + LIGNES (maître/détail)
# ---------------------------------------------------------------------------

class LigneCommandeInline(admin.TabularInline):
    model   = LigneCommande
    extra   = 1
    fields  = ('nom_produit', 'quantite', 'prix_unitaire')


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display  = ('numero_commande', 'client', 'boutique', 'statut',
                     'montant_total', 'date_creation')
    list_filter   = ('statut', 'boutique', 'date_creation')
    search_fields = ('numero_commande', 'client__nom_complet', 'client__whatsapp_numero')
    readonly_fields = ('numero_commande', 'date_creation', 'date_maj')
    inlines       = [LigneCommandeInline]


@admin.register(LigneCommande)
class LigneCommandeAdmin(admin.ModelAdmin):
    list_display = ('commande', 'nom_produit', 'quantite', 'prix_unitaire')


# ---------------------------------------------------------------------------
# TEMPLATE
# ---------------------------------------------------------------------------

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display  = ('nom', 'type', 'boutique', 'actif', 'date_creation')
    list_filter   = ('type', 'actif', 'boutique')
    search_fields = ('nom',)


# ---------------------------------------------------------------------------
# MESSAGE
# ---------------------------------------------------------------------------

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = ('commande', 'statut_envoi', 'template', 'date_envoi', 'date_reponse')
    list_filter   = ('statut_envoi',)
    search_fields = ('commande__numero_commande', 'contenu_envoye')
    readonly_fields = ('date_envoi',)
