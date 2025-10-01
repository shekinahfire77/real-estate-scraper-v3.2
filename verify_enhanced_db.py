#!/usr/bin/env python3
"""Verify enhanced database has comprehensive data"""

from src.database.connection import DatabaseConnection
from src.database.models import Property

db = DatabaseConnection(db_type='sqlite', db_path='data/real_estate_enhanced.db')

with db.get_session() as session:
    props = session.query(Property).all()

    print(f'Total properties in database: {len(props)}')
    print('='*80)

    for i, p in enumerate(props, 1):
        print(f'\n[Property {i}]')
        print(f'  Address: {p.address}')
        print(f'  Price: ${p.price:,.0f}' if p.price else '  Price: None')
        print(f'  Beds: {p.bedrooms}  |  Baths: {p.bathrooms}  |  Sqft: {p.square_footage}')
        print(f'  Page Type: {p.page_type}')
        print(f'  Listing ID: {p.listing_id}')

        # Show new fields
        if p.photos:
            photo_count = len(p.photos.split(','))
            print(f'  Photos: {photo_count} photos found')

        if p.property_description:
            desc_preview = p.property_description[:80] + '...'
            print(f'  Description: {desc_preview}')

        if p.property_history:
            history_preview = p.property_history[:80] + '...'
            print(f'  Property History: {history_preview}')

        if p.amenities:
            amenities_preview = p.amenities[:80] + '...'
            print(f'  Amenities: {amenities_preview}')

        # Count non-null fields
        all_fields = [
            p.url, p.listing_id, p.price, p.address, p.bedrooms, p.bathrooms,
            p.square_footage, p.page_type, p.property_description, p.photos,
            p.days_on_market, p.property_history, p.monthly_rent, p.security_deposit,
            p.lease_terms, p.amenities, p.pet_policy, p.contact_info,
            p.availability_date, p.application_requirements, p.parking
        ]
        non_null_count = sum(1 for field in all_fields if field is not None)
        print(f'  Fields with data: {non_null_count}/21')

    print('\n' + '='*80)
    print('Summary:')
    print(f'  Total properties: {len(props)}')
    print(f'  All classified as: {", ".join(set(p.page_type for p in props))}')
    print(f'  Avg fields per property: {sum(sum(1 for field in [p.url, p.listing_id, p.price, p.address, p.bedrooms, p.bathrooms, p.square_footage, p.page_type, p.property_description, p.photos, p.days_on_market, p.property_history, p.monthly_rent, p.security_deposit, p.lease_terms, p.amenities, p.pet_policy, p.contact_info, p.availability_date, p.application_requirements, p.parking] if field is not None) for p in props) / len(props):.1f}')
