from flask import Blueprint, render_template, request, redirect, url_for, session, flash

shop_bp = Blueprint('shop', __name__)

# ── Static shop data keyed by location ──────────────────────────────────────
SHOPS_BY_LOCATION = {
    'namaskar_chowk': [
        {
            'id': 'shree_ram_kirana',
            'name': 'Shree Ram Kirana Store',
            'owner': 'Ramesh Sharma',
            'address': 'Shop 4, Namaskar Chowk Market',
            'distance': '0.3 km',
            'rating': 4.8,
            'reviews': 312,
            'tag': 'Most Popular',
            'tag_color': '#e65100',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=500&q=80',
        },
        {
            'id': 'patel_general',
            'name': 'Patel General Store',
            'owner': 'Kamlesh Patel',
            'address': 'Main Road, Namaskar Chowk',
            'distance': '0.6 km',
            'rating': 4.5,
            'reviews': 198,
            'tag': 'Top Rated',
            'tag_color': '#2e7d32',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=500&q=80',
        },
        {
            'id': 'annapurna_grocery',
            'name': 'Annapurna Grocery Mart',
            'owner': 'Vijay Tiwari',
            'address': 'Lane 7, Namaskar Chowk',
            'distance': '0.9 km',
            'rating': 4.3,
            'reviews': 154,
            'tag': 'Fresh Items',
            'tag_color': '#1565c0',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?w=500&q=80',
        },
        {
            'id': 'fresh_daily',
            'name': 'Fresh Daily Mart',
            'owner': 'Sunita Verma',
            'address': 'Near Bus Stop, Namaskar Chowk',
            'distance': '1.2 km',
            'rating': 4.1,
            'reviews': 87,
            'tag': 'Budget Friendly',
            'tag_color': '#6a1b9a',
            'open': False,
            'image': 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=500&q=80',
        },
        {
            'id': 'sharma_brothers',
            'name': 'Sharma Brothers Store',
            'owner': 'Rakesh Sharma',
            'address': 'Opposite Park, Namaskar Chowk',
            'distance': '1.5 km',
            'rating': 4.0,
            'reviews': 62,
            'tag': 'Wholesale',
            'tag_color': '#37474f',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1519566335946-e6f65f0f4fdf?w=500&q=80',
        },
    ],
    'anand_nagar': [
        {
            'id': 'shree_ram_kirana',
            'name': 'Shree Ram Kirana Store',
            'owner': 'Ramesh Sharma',
            'address': 'Block A, Anand Nagar',
            'distance': '0.4 km',
            'rating': 4.8,
            'reviews': 290,
            'tag': 'Most Popular',
            'tag_color': '#e65100',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=500&q=80',
        },
        {
            'id': 'lucky_kirana',
            'name': 'Lucky Kirana Shop',
            'owner': 'Dinesh Gupta',
            'address': 'Market Road, Anand Nagar',
            'distance': '0.7 km',
            'rating': 4.4,
            'reviews': 175,
            'tag': 'Trusted',
            'tag_color': '#2e7d32',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=500&q=80',
        },
        {
            'id': 'new_india_mart',
            'name': 'New India Mart',
            'owner': 'Ashok Singh',
            'address': 'Near School, Anand Nagar',
            'distance': '1.0 km',
            'rating': 4.2,
            'reviews': 133,
            'tag': 'Fresh Items',
            'tag_color': '#1565c0',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?w=500&q=80',
        },
        {
            'id': 'royal_grocery',
            'name': 'Royal Grocery Store',
            'owner': 'Pooja Mehta',
            'address': 'Sector 2, Anand Nagar',
            'distance': '1.3 km',
            'rating': 4.0,
            'reviews': 99,
            'tag': 'Budget Friendly',
            'tag_color': '#6a1b9a',
            'open': False,
            'image': 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=500&q=80',
        },
        {
            'id': 'jain_supermart',
            'name': 'Jain Super Mart',
            'owner': 'Suresh Jain',
            'address': 'Main Square, Anand Nagar',
            'distance': '1.6 km',
            'rating': 3.9,
            'reviews': 55,
            'tag': 'Wholesale',
            'tag_color': '#37474f',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1519566335946-e6f65f0f4fdf?w=500&q=80',
        },
    ],
    'shree_nagar': [
        {
            'id': 'shree_ram_kirana',
            'name': 'Shree Ram Kirana Store',
            'owner': 'Ramesh Sharma',
            'address': 'Shree Nagar Chowk',
            'distance': '0.2 km',
            'rating': 4.8,
            'reviews': 341,
            'tag': 'Most Popular',
            'tag_color': '#e65100',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=500&q=80',
        },
        {
            'id': 'balaji_kirana',
            'name': 'Balaji Kirana Store',
            'owner': 'Mahesh Agrawal',
            'address': 'Near Temple, Shree Nagar',
            'distance': '0.5 km',
            'rating': 4.6,
            'reviews': 210,
            'tag': 'Trusted',
            'tag_color': '#2e7d32',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1578916171728-46686eac8d58?w=500&q=80',
        },
        {
            'id': 'ganesh_mart',
            'name': 'Ganesh General Mart',
            'owner': 'Naresh Chouhan',
            'address': 'Colony Road, Shree Nagar',
            'distance': '0.8 km',
            'rating': 4.2,
            'reviews': 144,
            'tag': 'Fresh Items',
            'tag_color': '#1565c0',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1604719312566-8912e9227c6a?w=500&q=80',
        },
        {
            'id': 'city_superstore',
            'name': 'City Super Store',
            'owner': 'Bhavna Joshi',
            'address': 'Opposite Garden, Shree Nagar',
            'distance': '1.1 km',
            'rating': 4.0,
            'reviews': 78,
            'tag': 'Budget Friendly',
            'tag_color': '#6a1b9a',
            'open': False,
            'image': 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=500&q=80',
        },
        {
            'id': 'krishna_kirana',
            'name': 'Krishna Kirana Bhandar',
            'owner': 'Gopal Yadav',
            'address': 'End Lane, Shree Nagar',
            'distance': '1.4 km',
            'rating': 3.8,
            'reviews': 41,
            'tag': 'Wholesale',
            'tag_color': '#37474f',
            'open': True,
            'image': 'https://images.unsplash.com/photo-1519566335946-e6f65f0f4fdf?w=500&q=80',
        },
    ],
}

LOCATION_DISPLAY = {
    'namaskar_chowk': 'Namaskar Chowk',
    'anand_nagar': 'Anand Nagar',
    'shree_nagar': 'Shree Nagar',
}


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('current_user'):
            flash('Please login to continue.', 'error')
            return redirect(url_for('user.login'))
        return f(*args, **kwargs)
    return decorated


@shop_bp.route('/location')
@login_required
def location():
    current_user = session.get('current_user')

    _LOCATION_META = {
        'namaskar_chowk': {'emoji': '🏪', 'key_short': 'namaskar',
                           'description': 'Busy market with 5 nearby kirana shops.',
                           'lat': 18.4088, 'lng': 76.5604},
        'anand_nagar':    {'emoji': '🏘️', 'key_short': 'anand',
                           'description': 'Residential colony with trusted grocery stores.',
                           'lat': 18.4120, 'lng': 76.5650},
        'shree_nagar':    {'emoji': '🛒', 'key_short': 'shree',
                           'description': 'Modern locality with supermarkets nearby.',
                           'lat': 18.4060, 'lng': 76.5580},
    }

    location_cards = []
    for key, shops in SHOPS_BY_LOCATION.items():
        meta       = _LOCATION_META.get(key, {})
        open_count = sum(1 for s in shops if s.get('open', True))
        location_cards.append({
            'key':         key,
            'name':        LOCATION_DISPLAY.get(key, key),
            'description': meta.get('description', ''),
            'emoji':       meta.get('emoji', '📍'),
            'lat':         meta.get('lat', 18.40),
            'lng':         meta.get('lng', 76.56),
            'shop_count':  len(shops),
            'open_count':  open_count,
            'url':         url_for('shop.shops', location=key),
        })

    return render_template('location.html',
                           current_user=current_user,
                           location_cards=location_cards)


@shop_bp.route('/shops')
@login_required
def shops():
    # Accept both ?location= (blueprint) and ?loc= (app.py style)
    location_key = (request.args.get('location') or
                    request.args.get('loc', '')).lower().replace(' ', '_').replace('-', '_')

    if location_key not in SHOPS_BY_LOCATION:
        flash('Invalid location selected. Please try again.', 'error')
        return redirect(url_for('shop.location'))

    shop_list     = SHOPS_BY_LOCATION[location_key]
    location_name = LOCATION_DISPLAY.get(location_key, location_key)
    current_user  = session.get('current_user')
    return render_template(
        'shops.html',
        shops=shop_list,
        location=location_name,
        location_key=location_key,
        current_user=current_user,
    )
