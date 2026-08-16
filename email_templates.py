"""
PressKitLive — HTML Email Templates (email_templates.py)
Styled HTML templates using PressKitLive dark / Spotify green design system.
"""

def _base_email_wrapper(title, content_html):
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      margin: 0; padding: 0; background-color: #060606; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #ffffff;
    }}
    .email-container {{
      max-width: 580px; margin: 30px auto; background-color: #121214; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }}
    .email-header {{
      background: linear-gradient(135deg, #121214 0%, #1a1a1e 100%); padding: 32px; text-align: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }}
    .email-brand {{
      font-size: 24px; font-weight: 900; color: #ffffff; letter-spacing: -0.5px; text-decoration: none;
    }}
    .email-brand-accent {{
      color: #1DB954;
    }}
    .email-body {{
      padding: 32px; line-height: 1.6; font-size: 15px; color: #d4d4d8;
    }}
    .email-body h2 {{
      color: #ffffff; font-size: 20px; font-weight: 800; margin-top: 0; margin-bottom: 16px;
    }}
    .email-btn {{
      display: inline-block; background-color: #1DB954; color: #000000 !important; font-weight: 800; font-size: 15px; padding: 14px 28px; border-radius: 30px; text-decoration: none; margin: 20px 0; text-align: center; box-shadow: 0 4px 14px rgba(29, 185, 84, 0.4);
    }}
    .email-box {{
      background-color: #18181b; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; margin: 20px 0; font-family: monospace; font-size: 14px; color: #ffffff;
    }}
    .email-footer {{
      padding: 24px 32px; background-color: #09090b; border-top: 1px solid rgba(255, 255, 255, 0.08); text-align: center; font-size: 12px; color: #71717a;
    }}
    .email-footer a {{
      color: #1DB954; text-decoration: none;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="email-header">
      <div class="email-brand">PressKit<span class="email-brand-accent">Live</span></div>
    </div>
    <div class="email-body">
      {content_html}
    </div>
    <div class="email-footer">
      <p>© 2026 PressKitLive — Sanatçı & Menajer Portalı. Tüm Hakları Saklıdır.</p>
      <p>Bir <a href="https://dijitalgru.com/" target="_blank">DijitalGru™ Yazılım Teknolojisi</a></p>
    </div>
  </div>
</body>
</html>"""

def render_welcome_email(name):
    content = f"""
      <h2>PressKitLive'a Hoş Geldiniz, {name}! 🎉</h2>
      <p>Hesabınız başarıyla oluşturuldu. Artık yüksek çözünürlüklü (300 DPI) medya depolarınızı, konser fotoğraflarınızı ve kilitli basın kitlerinizi profesyonel bir şekilde yönetebilirsiniz.</p>
      <p>Hemen yönetim panelinize giriş yaparak ilk sanatçınızı veya presskit sayfanızı yayınlayabilirsiniz.</p>
      <div style="text-align: center;">
        <a href="https://presskitlive.com/login.html" class="email-btn">Yönetim Paneline Giriş Yap</a>
      </div>
      <p style="font-size:13px; color:#a1a1aa;">Sorularınız veya yardım talepleriniz için bu e-postayı yanıtlayabilir ya da destek ekibimizle iletişime geçebilirsiniz.</p>
    """
    return _base_email_wrapper("PressKitLive'a Hoş Geldiniz!", content)

def render_password_reset_email(name, reset_link):
    content = f"""
      <h2>Şifre Sıfırlama Talebi</h2>
      <p>Sayın {name},</p>
      <p>PressKitLive hesabınız için bir şifre sıfırlama talebinde bulunuldu. Şifrenizi yenilemek için aşağıdaki butona tıklayın:</p>
      <div style="text-align: center;">
        <a href="{reset_link}" class="email-btn">Şifremi Sıfırla</a>
      </div>
      <p>Veya aşağıdaki bağlantıyı tarayıcınıza yapıştırın:</p>
      <div class="email-box">{reset_link}</div>
      <p style="font-size:13px; color:#eab308;">⚠️ Bu bağlantı güvenlik nedeniyle <strong>30 dakika</strong> geçerlidir. Eğer şifre sıfırlama talebinde bulunmadıysanız, bu e-postayı güvenle göz ardı edebilirsiniz.</p>
    """
    return _base_email_wrapper("Şifre Sıfırlama Talebiniz", content)

def render_free_membership_email(name, email, temp_password):
    content = f"""
      <h2>Ücretsiz Üyeliğiniz Hazır! 🎁</h2>
      <p>Sayın {name},</p>
      <p>PressKitLive yöneticisi tarafından hesabınıza <strong>Pro Ajans Paketi</strong> hediye üyelik olarak tanımlanmıştır.</p>
      <p>Giriş bilgileriniz aşağıdadır:</p>
      <div class="email-box">
        <strong>E-posta:</strong> {email}<br>
        <strong>Geçici Şifre:</strong> {temp_password}
      </div>
      <p>Güvenliğiniz için sisteme ilk girişinizden sonra şifrenizi değiştirmenizi tavsiye ederiz.</p>
      <div style="text-align: center;">
        <a href="https://presskitlive.com/login.html" class="email-btn">Hemen Giriş Yap</a>
      </div>
    """
    return _base_email_wrapper("Ücretsiz Üyeliğiniz Hazır", content)

def render_payment_success_email(name, plan_name):
    content = f"""
      <h2>Ödemeniz Alındı ve Aboneliğiniz Aktifleşti! ✅</h2>
      <p>Sayın {name},</p>
      <p><strong>{plan_name.upper()} Paketi</strong> abonelik ödemeniz başarıyla gerçekleşmiştir. Sanatçı kotanız ve 300 DPI yüksek çözünürlüklü indirme özellikleriniz hesabınıza tanımlanmıştır.</p>
      <div style="text-align: center;">
        <a href="https://presskitlive.com/agency_dashboard.html" class="email-btn">Paneli Görüntüle</a>
      </div>
    """
    return _base_email_wrapper("Aboneliğiniz Aktifleşti!", content)

def render_payment_failed_email(name, plan_name, update_card_link):
    content = f"""
      <h2>⚠️ Dikkat: Abonelik Ödemeniz Alınamadı</h2>
      <p>Sayın {name},</p>
      <p><strong>{plan_name.upper()} Paketi</strong> abonelik yenileme tahsilatı kartınızdan gerçekleştirilemedi. PressKit sayfalarınızın kesintiye uğramaması için lütfen kart bilgilerinizi güncelleyiniz.</p>
      <div style="text-align: center;">
        <a href="{update_card_link}" class="email-btn" style="background-color:#EF4444; color:#ffffff !important;">Kart Bilgilerini Güncelle</a>
      </div>
    """
    return _base_email_wrapper("Önemli: Ödeme Alınamadı", content)

def render_cancellation_email(name, plan_name, end_date):
    content = f"""
      <h2>Abonelik İptal Talebiniz Alındı</h2>
      <p>Sayın {name},</p>
      <p><strong>{plan_name.upper()} Paketi</strong> abonelik iptal talebiniz sistemimize işlenmiştir.</p>
      <p>Mevcut ödeme döneminizin sonu olan <strong>{end_date}</strong> tarihine kadar tüm ayrıcalıklarınız ve presskit sayfalarınız aktif kalmaya devam edecektir.</p>
      <p>Her zaman aramıza yeniden katılarak paketinizi aktifleştirebilirsiniz.</p>
    """
    return _base_email_wrapper("Abonelik İptal Talebi", content)
