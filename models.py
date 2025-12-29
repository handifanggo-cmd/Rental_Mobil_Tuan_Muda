from supabase import Client

class Mobil:
    def __init__(self, supabase_client: Client):
        self.db = supabase_client
        self.table = "mobil"

    def get_all(self):
        return self.db.table(self.table).select("*").order("id").execute()

    def get_by_id(self, id):
        return self.db.table(self.table).select("*").eq("id", id).single().execute()

    def update(self, id, data):
        return self.db.table(self.table).update(data).eq("id", id).execute()

    def delete(self, id):
        return self.db.table(self.table).delete().eq("id", id).execute()

class Transaksi:
    def __init__(self, supabase_client: Client):
        self.db = supabase_client
        self.table = "transaksi"

    def get_laporan(self):
        # Mengambil semua data transaksi beserta info mobil untuk Admin
        return self.db.table(self.table).select("*, mobil(*)").order("id", desc=True).execute()

    def buat_pesanan(self, data):
        return self.db.table(self.table).insert(data).execute()

    # WAJIB ADA: Agar Admin bisa mengubah status Pending -> Disewa -> Selesai
    def update_status(self, id, status):
        return self.db.table(self.table).update({"status_transaksi": status}).eq("id", id).execute()

class User:
    def __init__(self, supabase_client: Client):
        self.db = supabase_client
        self.table = "users"

    def login(self, username, password, role):
        return self.db.table(self.table).select("*").eq("username", username).eq("password", password).eq("role", role).execute()

    def register(self, data):
        return self.db.table(self.table).insert(data).execute()