import csv
import os
import time
import subprocess
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.headerregistry import Address

load_dotenv()

# Variables from .env file
BIRTHDAYS_CSV = os.getenv('BIRTHDAYS_CSV', 'birthdays.csv')
SMTP_HOST     = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT     = int(os.getenv('SMTP_PORT', 587))
SMTP_USER     = os.getenv('SMTP_USER', '')
SMTP_PASS     = os.getenv('SMTP_PASS', '')
FROM_EMAIL    = os.getenv('FROM_EMAIL', SMTP_USER)
FROM_NAME     = os.getenv('FROM_NAME', 'Cenomi')

FontPath = Path(os.getcwd()) / "open-sans/OpenSans-Bold.ttf"
OutputDir = Path("docs")
OutputDir.mkdir(exist_ok=True)

# Load people (name,email,birthdate,anniversary) from CSV file
def load_people(csv_file):
    people = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            name      = row[0].strip()
            email     = row[1].strip()
            try:
                birthdate = datetime.strptime(row[2].strip(), '%Y-%m-%d').date()
            except:
                continue
            anniversary = None
            if len(row) >= 4 and row[3].strip():
                try:
                    anniversary = datetime.strptime(row[3].strip(), '%Y-%m-%d').date()
                except:
                    anniversary = None
            people.append({
                'name':        name,
                'email':       email,
                'birthdate':   birthdate,
                'anniversary': anniversary
            })
    return people

def is_today(d):
    return d and (d.month, d.day) == (date.today().month, date.today().day)

# Draw the name on a base image
def draw_name_on_image(base_image_path, name, out_file):
    img      = Image.open(base_image_path).convert("RGB")
    draw     = ImageDraw.Draw(img)
    font     = ImageFont.truetype(str(FontPath), 36)
    basename = os.path.basename(base_image_path)

    if 'Anniversary' in basename and not basename.lower().endswith('_web.jpeg'):
        # email anniversary image
        text = f"Happy Anniversary, {name}"
        x, y = 785, 235
        draw.text((x, y), text, font=ImageFont.truetype(str(FontPath), 42), fill="white", spacing=-2)
    else:
        # birthday or other
        text = name
        x, y = 865, 140    # birthday coords
        draw.text((x, y), text, font=font, fill="white", spacing=-2)
    img.save(out_file)

# Draw the web-version anniversary image
def draw_anniversary_web_image(name, out_file):
    img  = Image.open("Anniversary_web.jpeg").convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FontPath), 42)
    text = f"Happy Anniversary, {name}"
    x, y = 785, 235   # anniversary‐web coords

    draw.text((x, y), text, font=font, fill="white", spacing=-2)
    img.save(out_file)

# Generate HTML for birthdays
def generate_birthday_page(name, img_path):
    img_name  = img_path.name
    html_path = img_path.with_suffix('.html')
    html_path.write_text(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Happy Birthday</title>
<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
<style>
body {{margin:0;background:#1a1a1a;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:sans-serif}}
img  {{max-width:90%;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.4)}}
#controls {{margin-top:20px;font-size:2em;cursor:pointer;background:none;border:none;color:#fff}}
</style></head><body>
<audio id="music" loop><source src="happy_birthday.mp3" type="audio/mpeg"></audio>
<img src="{img_name}" alt="Birthday"><button id="controls">▶️</button>
<p>Wishing you a joyful day</p>
<script>
const audio=document.getElementById('music'),btn=document.getElementById('controls');
btn.addEventListener('click',()=>{{ if(audio.paused){{ audio.play(); btn.textContent='⏸'; launch(); }} else {{ audio.pause(); btn.textContent='▶️'; }} }});
document.body.addEventListener('click',()=>{{ if(audio.paused){{ audio.play().then(()=>{{ btn.textContent='⏸'; launch(); }}); }} }},{{ once:true }});
function launch(){{ 
  var count=200,defaults={{origin:{{y:0.7}}}};
  function fire(p,o){{ confetti(Object.assign({{}},defaults,o,{{particleCount:Math.floor(count*p)}})); }}
  fire(0.25,{{spread:26,startVelocity:55}});
  fire(0.2,{{spread:60}});
  fire(0.35,{{spread:100,decay:0.91,scalar:0.8}});
  fire(0.1,{{spread:120,startVelocity:25,decay:0.92,scalar:1.2}});
  fire(0.1,{{spread:120,startVelocity:45}});
}}
</script></body></html>
""", encoding='utf-8')

# Generate HTML for anniversaries
def generate_anniversary_page(name, img_path):
    img_name  = img_path.name
    html_path = img_path.with_suffix('.html')
    html_path.write_text(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Happy Work Anniversary</title>
<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
<style>
body {{margin:0;background:#1a1a1a;color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:sans-serif}}
img  {{max-width:90%;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.4)}}
p    {{margin-top:20px;font-size:1.2em}}
</style></head><body>
<img src="{img_name}" alt="Anniversary"><p>Wishing you continued success 🎉</p>
<script>
var duration=10000,end=Date.now()+duration,defaults={{startVelocity:30,spread:360,ticks:60,zIndex:0}};
function rand(min,max){{return Math.random()*(max-min)+min;}}
var iv=setInterval(()=>{{ var tl=end-Date.now(); if(tl<=0) return clearInterval(iv);
  var cnt=50*(tl/duration);
  confetti(Object.assign({{}},defaults,{{particleCount:cnt,origin:{{x:rand(0.1,0.3),y:Math.random()-0.2}}}}));
  confetti(Object.assign({{}},defaults,{{particleCount:cnt,origin:{{x:rand(0.7,0.9),y:Math.random()-0.2}}}}));
}},250);
</script></body></html>
""", encoding='utf-8')

# Send email for either birthday or anniversary
def send_email(name, email, img_path, subject, web_html_filename=None):
    if web_html_filename:
        url = f"https://yasirkhan36.github.io/BirthdayWish/{web_html_filename}"
    else:
        url = f"https://yasirkhan36.github.io/BirthdayWish/{img_path.stem}.html"
    msg = MIMEMultipart("related")
    msg['Subject'] = subject
    msg['From']    = str(Address(FROM_NAME, FROM_EMAIL))
    msg['To']      = email

    msg.attach(MIMEText(f"""
<html>
  <body style="font-family:sans-serif; background-color:#fff;">
    <div style="max-width:600px; margin:20px auto;">
      <p>Dear {name},</p>
      <a href="{url}" target="_blank">
        <img src="cid:img" style="width:100%; border-radius:8px;">
      </a>
    </div>
  </body>
</html>
""", "html"))

    with open(img_path, "rb") as f:
        img = MIMEImage(f.read())
        img.add_header("Content-ID", "<img>")
        msg.attach(img)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)

# Main function to build pages and send emails
def main():
    people = load_people(BIRTHDAYS_CSV)
    queue  = []

    for p in people:
        name  = p['name']
        email = p['email']
        safe  = name.lower().replace(" ", "_")

        if is_today(p['birthdate']):
            out = OutputDir / f"{safe}_birthday.jpeg"
            draw_name_on_image("BdayWish.jpeg", name, out)
            generate_birthday_page(name, out)
            queue.append((name, email, out, f"Happy Birthday, {name.split()[0]}", None))

        if is_today(p['anniversary']):
            email_out = OutputDir / f"{safe}_anniversary.jpeg"
            draw_name_on_image("Anniversary.jpeg", name, email_out)

            web_out = OutputDir / f"{safe}_anniversary_web.jpeg"
            draw_anniversary_web_image(name, web_out)
            generate_anniversary_page(name, web_out)

            queue.append((
                name,
                email,
                email_out,
                f"Happy Work Anniversary, {name.split()[0]}",
                web_out.with_suffix('.html').name
            ))

    subprocess.run(["git", "add", "docs/"])
    subprocess.run(["git", "commit", "-m", "Update pages"], check=False)
    subprocess.run(["git", "push"])
    time.sleep(5)

    for nm, em, ip, subj, web_html in queue:
        try:
            send_email(nm, em, ip, subj, web_html)
            print(f"✅ Sent to {nm} <{em}>")
        except Exception as err:
            print(f"❌ Failed for {nm}: {err}")

if __name__ == "__main__":
    main()