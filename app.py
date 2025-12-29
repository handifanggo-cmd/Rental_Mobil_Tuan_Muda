import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
from dotenv import load_dotenv
from models import Mobil, Transaksi, User


load_dotenv()

print("--- DEBUG CONNECTION ---")
print(f"DEBUG URL: {os.getenv('SUPABASE_URL')}")
print(f"DEBUG KEY: {os.getenv('SUPABASE_KEY')}")
print("------------------------")

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "autodrive-key-2025")


url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)


db_mobil = Mobil(supabase)
db_transaksi = Transaksi(supabase)
db_user = User(supabase)

# --- MIDDLEWARE / HELPER ---
@app.template_filter('format_rupiah')
def format_rupiah(value):
    if value is None:
        return "0"
    return "{:,.0f}".format(value).replace(',', '.')

# --- ROUTES UTAMA ---

@app.route('/')
def index():
    res = db_mobil.get_all()
    return render_template('index.html', mobil=res.data)

# --- AUTH ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = {
            "username": request.form.get('username'),
            "password": request.form.get('password'),
            "nama_lengkap": request.form.get('nama'),
            "role": "customer"
        }
        db_user.register(data)
        flash("Pendaftaran berhasil! Silakan login.", "success")
        return redirect(url_for('login_customer'))
    return render_template('register.html')

@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        res = db_user.login(request.form.get('username'), request.form.get('password'), 'admin')
        if res.data:
            session.update({'user_id': res.data[0]['id'], 'role': 'admin', 'username': res.data[0]['username']})
            return redirect(url_for('dashboard_admin'))
        flash("Login Admin Gagal!", "danger")
    return render_template('login_admin.html')

@app.route('/login/customer', methods=['GET', 'POST'])
def login_customer():
    if request.method == 'POST':
        res = db_user.login(request.form.get('username'), request.form.get('password'), 'customer')
        if res.data:
            session.update({'user_id': res.data[0]['id'], 'role': 'customer', 'username': res.data[0]['username']})
            return redirect(url_for('dashboard_customer'))
        flash("Login Customer Gagal!", "danger")
    return render_template('login_customer.html')

# --- ADMIN ROUTES ---

@app.route('/admin/dashboard')
def dashboard_admin():
    if session.get('role') != 'admin': 
        return redirect(url_for('login_admin'))
    mobs = db_mobil.get_all()
    laps = db_transaksi.get_laporan()
    return render_template('dashboard_admin.html', mobil=mobs.data, laporan=laps.data)

@app.route('/admin/transaksi/update/<int:id>/<status>')
def update_status_transaksi(id, status):
    if session.get('role') != 'admin':
        return redirect(url_for('login_admin'))
    
    db_transaksi.update_status(id, status)
    
    if status == 'Selesai':
        res_transaksi = supabase.table("transaksi").select("mobil_id").eq("id", id).single().execute()
        if res_transaksi.data:
            m_id = res_transaksi.data['mobil_id']
            res_mobil = db_mobil.get_by_id(m_id)
            db_mobil.update(m_id, {"stok": res_mobil.data['stok'] + 1})
            
    flash(f"Transaksi diupdate ke: {status}", "success")
    return redirect(url_for('dashboard_admin'))

@app.route('/admin/mobil/tambah', methods=['GET', 'POST'])
def tambah_mobil():
    if session.get('role') != 'admin': 
        return redirect(url_for('login_admin'))
    if request.method == 'POST':
        data = {
            "nama_mobil": request.form.get('nama'),
            "merk": request.form.get('merk'),
            "harga_sewa": int(request.form.get('harga')),
            "stok": int(request.form.get('stok')),
            "foto_url": request.form.get('foto_url'),
            "deskripsi": request.form.get('deskripsi'),
            "status": "Tersedia"
        }
        supabase.table("mobil").insert(data).execute()
        flash("Mobil berhasil ditambahkan!", "success")
        return redirect(url_for('dashboard_admin'))
    return render_template('insert_mobil.html')

@app.route('/admin/mobil/edit/<int:id>', methods=['GET', 'POST'])
def edit_mobil(id):
    if session.get('role') != 'admin': 
        return redirect(url_for('login_admin'))

    if request.method == 'POST':
        data = {
            "nama_mobil": request.form.get('nama'), 
            "merk": request.form.get('merk'),
            "harga_sewa": int(request.form.get('harga')), 
            "stok": int(request.form.get('stok')),
            "foto_url": request.form.get('foto_url'),
            "deskripsi": request.form.get('deskripsi')
        }
        db_mobil.update(id, data)
        flash("Data armada berhasil diperbarui!", "success")
        return redirect(url_for('dashboard_admin'))

    res = db_mobil.get_by_id(id)
    return render_template('edit_mobil.html', data=res.data)

@app.route('/admin/mobil/hapus/<int:id>')
def hapus_mobil(id):
    if session.get('role') != 'admin': 
        return redirect(url_for('login_admin'))
    db_mobil.delete(id)
    flash("Armada berhasil dihapus!", "warning")
    return redirect(url_for('dashboard_admin'))

# --- CUSTOMER ROUTES ---

@app.route('/customer/dashboard')
def dashboard_customer():
    if session.get('role') != 'customer': 
        return redirect(url_for('login_customer'))
    mobs = db_mobil.get_all()
    return render_template('dashboard_customer.html', mobil=mobs.data)

@app.route('/customer/riwayat')
def riwayat_customer():
    if not session.get('user_id'):
        return redirect(url_for('login_customer'))
        
    res = supabase.table("transaksi").select("*, mobil(*)").eq("user_id", session['user_id']).execute()
    
    for t in res.data:
        d1 = datetime.strptime(t['tgl_mulai'], '%Y-%m-%d')
        d2 = datetime.strptime(t['tgl_selesai'], '%Y-%m-%d')
        durasi = (d2 - d1).days
        if durasi <= 0: durasi = 1
        t['total_biaya'] = durasi * t['mobil']['harga_sewa']
        
    return render_template('riwayat_customer.html', transaksi=res.data)

@app.route('/customer/book', methods=['POST'])
def book_mobil():
    if not session.get('user_id'): 
        return redirect(url_for('login_customer'))
    
    mobil_id = request.form.get('mobil_id')
    res_mobil = db_mobil.get_by_id(mobil_id)
    
    if res_mobil.data and res_mobil.data['stok'] > 0:
        data_sewa = {
            "user_id": session['user_id'],
            "mobil_id": mobil_id,
            "nama_penyewa": session['username'],
            "nomor_wa": request.form.get('nomor_wa'),
            "tgl_mulai": request.form.get('tgl_mulai'),
            "tgl_selesai": request.form.get('tgl_selesai'),
            "status_transaksi": "Pending"
        }
        db_transaksi.buat_pesanan(data_sewa)
        db_mobil.update(mobil_id, {"stok": res_mobil.data['stok'] - 1})
        flash("Booking berhasil!", "success")
    else:
        flash("Stok mobil habis!", "danger")
        
    return redirect(url_for('dashboard_customer'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


app = app 

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)