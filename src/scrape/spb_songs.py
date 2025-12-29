import yt_dlp
import os
spb_songs_data = [
    {"song_name": "O Papa Lali", "movie_name": "Geethanjali (1989)", "category": "Solo / Lullaby"},
    {"song_name": "Maate Raani", "movie_name": "O Papa Lali (1990)", "category": "Solo / Slow"},
    {"song_name": "Telusa Manasa", "movie_name": "Criminal (1994)", "category": "Solo / Breathy"},
    {"song_name": "Naa Cheli Rojave", "movie_name": "Roja (1992)", "category": "Solo / AR Rahman Mix"},
    {"song_name": "Jabilli Kosam", "movie_name": "Manchi Manasulu (1986)", "category": "Solo / Stable Pitch"},
    {"song_name": "Eduta Neeve", "movie_name": "Abbayigaru (1993)", "category": "Solo / Pathos"},
    {"song_name": "Okkadai Ravadam", "movie_name": "Pavitra Bandham (1996)", "category": "Solo / Emotional"},
    {"song_name": "Thakita Thadimi", "movie_name": "Sagara Sangamam (1983)", "category": "Solo / Classical"},
    {"song_name": "O Cheliya", "movie_name": "Premikudu (1994)", "category": "Solo / High Pitch"},
    {"song_name": "Prema Entha Madhuram", "movie_name": "Abhinandana (1988)", "category": "Solo / Deep"},
    {"song_name": "Subhalekha Rasukunna", "movie_name": "Kondaveeti Donga (1990)", "category": "Duet / Long Verses"},
    {"song_name": "Sundari Neeve", "movie_name": "Kshana Kshanam (1991)", "category": "Duet / Crisp Diction"},
    {"song_name": "Priya Raagale", "movie_name": "Hello Brother (1994)", "category": "Duet / Playful"},
    {"song_name": "Abbanee Tiyyani", "movie_name": "Jagadeka Veerudu Athiloka Sundari (1990)", "category": "Duet / Commercial"},
    {"song_name": "Balapam Patti", "movie_name": "Bobbili Raja (1990)", "category": "Duet / Folk"},
    {"song_name": "Chiluka Kshemama", "movie_name": "Rowdy Alludu (1991)", "category": "Duet / Fast Paced"},
    {"song_name": "Anjali Anjali", "movie_name": "Duet (1994)", "category": "Duet / Emotional"},
    {"song_name": "Guvva Gorinka Tho", "movie_name": "Khaidi No. 786 (1988)", "category": "Duet / Village Folk"},
    {"song_name": "Jaamu Rathiri", "movie_name": "Kshana Kshanam (1991)", "category": "Duet / Low Pitch Humming"},
    {"song_name": "Priyatama Na Hrudayama", "movie_name": "Prema (1989)", "category": "Duet / High Strain"},
    {"song_name": "Bangaru Kodipetta", "movie_name": "Gharana Mogudu (1992)", "category": "Mass / High Energy"},
    {"song_name": "Raamma Chilakamma", "movie_name": "Choodalani Vundi (1998)", "category": "Mass / Late 90s"},
    {"song_name": "Jagada Jagada", "movie_name": "Geethanjali (1989)", "category": "Mass / Anthem"},
    {"song_name": "Hello Guru", "movie_name": "Nirnayam (1991)", "category": "Mass / Conversational"},
    {"song_name": "Mukkala Mukkabula", "movie_name": "Premikudu (1994)", "category": "Mass / Rhythmic"},
    {"song_name": "O Pavurama", "movie_name": "Swayamvaram (1999)", "category": "Late 90s / Pathos"},
    {"song_name": "Nuvvu Naato Emannavo", "movie_name": "Nuvvu Naaku Nachav (2001)", "category": "Late 90s / Soft"},
    {"song_name": "Pedave Palikina", "movie_name": "Nani (2004)", "category": "Early 2000s / Isolation"},
    {"song_name": "Cheppave Prema", "movie_name": "Manasantha Nuvve (2001)", "category": "Early 2000s / Sad"},
    {"song_name": "Ammadu Appachi", "movie_name": "Indra (2002)", "category": "Early 2000s / Mass"},

    {"song_name": "Kannetika Kalavalu", "movie_name": "Mathru Devo Bhava (1993)", "category": "Deep Emotion / Slow"},
    {"song_name": "Raalipoye Puvva", "movie_name": "Mathru Devo Bhava (1993)", "category": "Deep Emotion / Solo"},
    {"song_name": "Emani Ne Cheppanu", "movie_name": "Seenu (1999)", "category": "Deep Emotion / Clear"},
    {"song_name": "Prema Ledani", "movie_name": "Abhinandana (1988)", "category": "Deep Emotion / Breakup"},
    {"song_name": "Chikati Musire", "movie_name": "Abbayigaru (1993)", "category": "Deep Emotion / Dark"},

    {"song_name": "Aura Ammaka Chella", "movie_name": "Apathbandhavudu (1992)", "category": "Technical / Diction"},
    {"song_name": "Om Namaha", "movie_name": "Geethanjali (1989)", "category": "Technical / Breath Control"},
    {"song_name": "Keeravani", "movie_name": "Anveshana (1985)", "category": "Technical / Cleanest Recording"},
    {"song_name": "Srirastu Subhamastu", "movie_name": "Pelli Pustakam (1991)", "category": "Technical / Traditional"},
    {"song_name": "Maa Perati Jamchettu", "movie_name": "Pelli Sandadi (1996)", "category": "Technical / Fast Flow"}
]

def download_and_organize(song_list):
    base_folder = "SPB_Dataset_Raw"
    
    for song in song_list:
        category_clean = song['category'].replace(" ", "_").replace("/", "-")
        song_clean = song['song_name'].replace(" ", "_")

        output_path = f"{base_folder}/{category_clean}/{song_clean}"

        query = f"{song['song_name']} {song['movie_name']} telugu song high quality audio"
        
        print(f"⬇️  Searching & Downloading: {song['song_name']}...")

        ydl_opts = {
            'format': 'bestaudio/best',  
            'outtmpl': output_path,      
            'default_search': 'ytsearch1', 
            'noplaylist': True,
            'quiet': True,              
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav', 
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])
            print(f" Done: {song['song_name']}")
        except Exception as e:
            print(f" Failed: {song['song_name']} | Error: {e}")

if __name__ == "__main__":
    print(" Starting Batch Download for SPB Dataset...")
    download_and_organize(spb_songs_data)
    print("\n Download Complete! Check the 'SPB_Dataset_Raw' folder.")