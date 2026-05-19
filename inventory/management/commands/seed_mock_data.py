from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db.models import Q

from inventory.models import Category, Product


class Command(BaseCommand):
    help = "Populate database with mock categories, products, groups, and users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing categories and products before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing categories and products deleted."))

        groups = ["admin", "client"]
        for group_name in groups:
            Group.objects.get_or_create(name=group_name)
        self.stdout.write(self.style.SUCCESS("Groups ensured: admin, client"))

        categories_data = [
            {"name": "Informatique Mobile", "description": "PC portables, tablettes et accessoires nomades"},
            {"name": "Périphériques", "description": "Claviers, souris, webcams et docks"},
            {"name": "Réseau & Connectivité", "description": "Wi-Fi, routeurs, switches et équipements mesh"},
            {"name": "Audio & Vidéo", "description": "Casques, micros, enceintes et solutions multimédia"},
            {"name": "Gaming", "description": "Consoles, manettes et accessoires de jeu"},
            {"name": "Bureau Intelligent", "description": "Équipements connectés pour bureaux modernes"},
        ]

        categories = {}
        for item in categories_data:
            category, _ = Category.objects.get_or_create(
                name=item["name"],
                defaults={"description": item["description"]},
            )
            if category.description != item["description"]:
                category.description = item["description"]
                category.save(update_fields=["description"])
            categories[item["name"]] = category

        products_data = [
            {
                "name": "Ultrabook Air 13",
                "description": "PC portable 16 Go RAM / SSD 1 To / autonomie longue durée",
                "price": Decimal("11499.00"),
                "stock": 14,
                "category": "Informatique Mobile",
            },
            {
                "name": "Tablette Pro 11",
                "description": "Tablette 11 pouces Wi-Fi + stylet inclus",
                "price": Decimal("6799.00"),
                "stock": 4,
                "category": "Informatique Mobile",
            },
            {
                "name": "Sacoche Antichoc 15",
                "description": "Sacoche renforcée pour ordinateur portable 14-15 pouces",
                "price": Decimal("289.00"),
                "stock": 31,
                "category": "Informatique Mobile",
            },
            {
                "name": "Clavier Compact Sans Fil",
                "description": "Clavier AZERTY silencieux multi-appareils",
                "price": Decimal("349.00"),
                "stock": 12,
                "category": "Périphériques",
            },
            {
                "name": "Souris Verticale Ergo",
                "description": "Souris ergonomique rechargeable USB-C",
                "price": Decimal("259.00"),
                "stock": 8,
                "category": "Périphériques",
            },
            {
                "name": "Webcam Full HD 60fps",
                "description": "Webcam autofocus avec double micro antibruit",
                "price": Decimal("599.00"),
                "stock": 6,
                "category": "Périphériques",
            },
            {
                "name": "Station d'Accueil USB-C 10-en-1",
                "description": "Dock avec HDMI 4K, Ethernet, SD et alimentation pass-through",
                "price": Decimal("990.00"),
                "stock": 9,
                "category": "Périphériques",
            },
            {
                "name": "Routeur Mesh AX3000",
                "description": "Routeur Wi-Fi 6 dual-band pour couverture étendue",
                "price": Decimal("1590.00"),
                "stock": 3,
                "category": "Réseau & Connectivité",
            },
            {
                "name": "Switch Gigabit 16 Ports",
                "description": "Switch manageable pour PME",
                "price": Decimal("1390.00"),
                "stock": 7,
                "category": "Réseau & Connectivité",
            },
            {
                "name": "Répéteur Wi-Fi 6",
                "description": "Amplificateur de signal pour grandes surfaces",
                "price": Decimal("520.00"),
                "stock": 11,
                "category": "Réseau & Connectivité",
            },
            {
                "name": "Casque Bluetooth ANC",
                "description": "Réduction active du bruit et autonomie 35h",
                "price": Decimal("899.00"),
                "stock": 2,
                "category": "Audio & Vidéo",
            },
            {
                "name": "Microphone USB Studio",
                "description": "Micro cardioïde plug-and-play pour réunion et streaming",
                "price": Decimal("749.00"),
                "stock": 13,
                "category": "Audio & Vidéo",
            },
            {
                "name": "Barre de Son 2.1",
                "description": "Barre de son avec caisson sans fil",
                "price": Decimal("2290.00"),
                "stock": 1,
                "category": "Audio & Vidéo",
            },
            {
                "name": "Console Nova X",
                "description": "Console de jeu 1 To avec manette sans fil",
                "price": Decimal("6990.00"),
                "stock": 6,
                "category": "Gaming",
            },
            {
                "name": "Manette Pro Sans Fil",
                "description": "Manette ergonomique avec retour haptique",
                "price": Decimal("890.00"),
                "stock": 17,
                "category": "Gaming",
            },
            {
                "name": "Pack Éclairage RGB",
                "description": "Kit lumineux synchronisé pour setup gaming",
                "price": Decimal("430.00"),
                "stock": 5,
                "category": "Gaming",
            },
            {
                "name": "Caméra IP 2K",
                "description": "Caméra connectée avec vision nocturne et détection intelligente",
                "price": Decimal("690.00"),
                "stock": 0,
                "category": "Bureau Intelligent",
            },
            {
                "name": "Prise Connectée Wi-Fi",
                "description": "Prise pilotable à distance avec suivi énergétique",
                "price": Decimal("149.00"),
                "stock": 27,
                "category": "Bureau Intelligent",
            },
        ]

        created_count = 0
        updated_count = 0
        image_backfilled_count = 0
        image_seeded_count = 0
        image_linked_count = 0

        for item in products_data:
            defaults = {
                "description": item["description"],
                "price": item["price"],
                "stock": item["stock"],
                "category": categories[item["category"]],
            }
            product, created = Product.objects.get_or_create(name=item["name"], defaults=defaults)

            if created:
                created_count += 1
            else:
                changed = False
                for field, value in defaults.items():
                    if getattr(product, field) != value:
                        setattr(product, field, value)
                        changed = True
                if changed:
                    product.save()
                    updated_count += 1

        media_products_dir = Path(settings.MEDIA_ROOT) / "products"
        allowed_image_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
        available_images = []

        if media_products_dir.exists() and media_products_dir.is_dir():
            available_images = sorted(
                file.name
                for file in media_products_dir.iterdir()
                if file.is_file() and file.suffix.lower() in allowed_image_ext
            )

        if available_images:
            def normalize_product_name(filename: str) -> str:
                stem = filename.rsplit(".", 1)[0]
                stem = stem.replace("_", " ").replace("-", " ")
                stem = " ".join(stem.split())
                return stem.title()

            def pick_category_key(filename: str) -> str:
                lower_name = filename.lower()
                if any(token in lower_name for token in ["airpod", "earpod", "casque", "audio", "headphone"]):
                    return "Audio & Vidéo"
                if any(token in lower_name for token in ["mouse", "keyboard", "charger", "magsafe", "dock", "airtag"]):
                    return "Périphériques"
                if any(
                    token in lower_name
                    for token in ["iphone", "mac", "macbook", "ultrabook", "ipad", "smartwatch", "studio", "mini"]
                ):
                    return "Informatique Mobile"
                return "Informatique Mobile"

            for image_name in available_images:
                product_name = normalize_product_name(image_name)
                if not product_name:
                    continue
                category_key = pick_category_key(image_name)
                category = categories.get(category_key) or next(iter(categories.values()))
                price_seed = sum(ord(ch) for ch in product_name)
                price = Decimal(str((price_seed % 9000) + 900))
                stock = (price_seed % 25) + 1

                product, created = Product.objects.get_or_create(
                    name=product_name,
                    defaults={
                        "description": "Produit importe depuis media.",
                        "price": price,
                        "stock": stock,
                        "category": category,
                        "photo": f"products/{image_name}",
                    },
                )

                if created:
                    image_seeded_count += 1
                else:
                    if not product.photo:
                        product.photo.name = f"products/{image_name}"
                        product.save(update_fields=["photo"])
                        image_linked_count += 1

            products_without_photo = Product.objects.filter(Q(photo="") | Q(photo__isnull=True))
            for product in products_without_photo:
                # Deterministic assignment so repeated seeds keep stable mock visuals.
                image_index = sum(ord(ch) for ch in product.name) % len(available_images)
                product.photo.name = f"products/{available_images[image_index]}"
                product.save(update_fields=["photo"])
                image_backfilled_count += 1
        else:
            self.stdout.write(
                self.style.WARNING(
                    "No image files found in media/products; products without photos were left unchanged."
                )
            )

        User = get_user_model()

        user_specs = [
            {
                "username": "superuser1",
                "group": "admin",
                "password": "SuperUser@2026",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "super1",
                "group": "admin",
                "password": "SuperAdmin@2026",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "admin1",
                "group": "admin",
                "password": "Admin@2026",
                "is_staff": True,
                "is_superuser": False,
            },
            {
                "username": "user1",
                "group": "client",
                "password": "Viewer@2026",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        for spec in user_specs:
            username = spec["username"]
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "is_staff": spec["is_staff"],
                    "is_superuser": spec["is_superuser"],
                },
            )

            fields_to_update = []
            if user.is_staff != spec["is_staff"]:
                user.is_staff = spec["is_staff"]
                fields_to_update.append("is_staff")
            if user.is_superuser != spec["is_superuser"]:
                user.is_superuser = spec["is_superuser"]
                fields_to_update.append("is_superuser")
            if fields_to_update:
                user.save(update_fields=fields_to_update)

            # Keep seeded credentials deterministic for local demo accounts.
            user.set_password(spec["password"])
            user.save(update_fields=["password"])

            group = Group.objects.get(name=spec["group"])
            user.groups.add(group)

        self.stdout.write(
            self.style.SUCCESS(
                f"Mock data ready: {Category.objects.count()} categories, "
                f"{Product.objects.count()} products "
                f"({created_count} created, {updated_count} updated, "
                f"{image_seeded_count} image products added, {image_linked_count} images linked, "
                f"{image_backfilled_count} images backfilled)."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Users ensured: superuser1, super1, admin1, user1 (passwords synced from CREDENTIALS.md)."
            )
        )
