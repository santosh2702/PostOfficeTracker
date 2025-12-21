import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import geocoder

# Load and SUPER CLEAN the data
@st.cache_data
def load_data():
    df = pd.read_csv('pincode_data.csv')  # Your actual file name

    # Keep only Delivery offices
    df = df[df['delivery'] == 'Delivery']

    # Convert to numeric (invalid → NaN)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Drop any row with NaN lat/long
    df = df.dropna(subset=['latitude', 'longitude'])

    # STRICTLY filter valid lat/long ranges
    df = df[
        (df['latitude'] >= -90) & (df['latitude'] <= 90) &
        (df['longitude'] >= -180) & (df['longitude'] <= 180)
    ]

    # India-specific bounds (this removes all invalid entries)
    df = df[
        (df['latitude'].between(6, 37)) & 
        (df['longitude'].between(68, 97))
    ]

    df['officename'] = df['officename'].str.strip()

    # Debug: Show how many rows were kept
    st.write(f"Total valid Delivery offices after cleaning: {len(df)}")

    return df

df = load_data()

# App Title
st.title("Post Office Nearby")
st.markdown("Find the nearest **Delivery Post Office** in India using your location or pincode.")

# Language selector
lang = st.selectbox("Language", ["English", "हिन्दी"])
if lang == "हिन्दी":
    st.markdown("**निकटतम डिलीवरी पोस्ट ऑफिस खोजें**")

# Option 1: Use current location
user_location = None
if st.button("Use My Current Location"):
    try:
        g = geocoder.ip('me')
        if g.ok and g.latlng:
            lat, lon = g.latlng
            user_location = (lat, lon)
            st.success(f"Detected location: {lat:.4f}, {lon:.4f}")
        else:
            st.error("Could not detect location. Please allow location access.")
    except Exception as e:
        st.error(f"Location detection failed: {e}")

# Option 2: Enter pincode or address
pincode_input = st.text_input("Or enter your Pincode / Village Name")
if pincode_input:
    # Try to find location from pincode
    pincode_row = df[df['pincode'].astype(str).str.startswith(pincode_input)]
    if not pincode_row.empty:
        user_location = (pincode_row.iloc[0]['latitude'], pincode_row.iloc[0]['longitude'])
        st.info(f"Using location near {pincode_row.iloc[0]['officename']}")
    else:
        # Fallback: geocode address
        try:
            g = geocoder.arcgis(pincode_input + ", India")
            if g.ok:
                user_location = (g.latlng[0], g.latlng[1])
                st.info("Found location using address.")
            else:
                st.warning("Could not find location.")
        except:
            st.warning("Enter a valid pincode or address.")

# If we have user location, calculate distances
if user_location:
    # Now it's SAFE to calculate distances
    df['distance_km'] = df.apply(
        lambda row: geodesic(user_location, (row['latitude'], row['longitude'])).km,
        axis=1
    )

    nearest = df.sort_values('distance_km').head(5)  # Top 5

    st.subheader("Nearest Delivery Post Offices")
    for _, row in nearest.iterrows():
        st.markdown(f"**{row['officename']}** ({row['pincode']})")
        st.markdown(f"Distance: **{row['distance_km']:.1f} km**")
        st.markdown(f"{row['district']}, {row['statename']}")
        st.markdown("---")

    # Map
    m = folium.Map(location=user_location, zoom_start=12)
    folium.Marker(user_location, popup="You are here", icon=folium.Icon(color='red', icon='user')).add_to(m)
    for _, row in nearest.iterrows():
        folium.Marker(
            [row['latitude'], row['longitude']],
            popup=f"{row['officename']} ({row['pincode']})<br>{row['distance_km']:.1f} km",
            tooltip=row['officename'],
            icon=folium.Icon(color='blue')
        ).add_to(m)
    st_folium(m, width=700, height=500)

else:
    st.info("Press 'Use My Current Location' or enter a pincode to start.")

# Footer
st.markdown("---")
st.markdown("**Powered by India Post Data** | Made for 1.4 billion Indians")