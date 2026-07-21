"""
CSS do fundo "tecnológico/futurista" do app: um planeta estilizado (CSS puro,
sem imagem externa) com destaque verde na região amazônica, gradientes azuis,
partículas discretas — e um "cartão" claro por trás do conteúdo pra não
prejudicar a leitura.
"""

CSS_FUNDO_FUTURISTA = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;
}

.stApp {
  background:
    /* brilho de atmosfera do planeta */
    radial-gradient(circle at 86% 18%, rgba(120, 210, 255, 0.28) 0%, rgba(120, 210, 255, 0) 30%),
    /* mancha verde estilizada = região amazônica */
    radial-gradient(ellipse 220px 170px at 82% 21%, #35b46a 0%, #1f7a45 45%, rgba(31,122,69,0) 70%),
    /* planeta (oceano) */
    radial-gradient(circle at 84% 20%, #2d6fb0 0%, #14335f 42%, rgba(10,20,40,0) 46%),
    /* névoa tecnológica */
    radial-gradient(circle at 10% 90%, rgba(60, 140, 255, 0.10) 0%, rgba(10,20,40,0) 55%),
    /* base */
    linear-gradient(150deg, #030712 0%, #071a34 45%, #0a2a52 100%);
  background-attachment: fixed;
  background-size: cover;
  position: relative;
}

/* partículas discretas (pontinhos tipo estrelas) */
.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  background-image:
    radial-gradient(rgba(255,255,255,0.55) 1px, transparent 1.4px),
    radial-gradient(rgba(150,200,255,0.4) 1px, transparent 1.4px);
  background-size: 160px 160px, 95px 95px;
  background-position: 0 0, 50px 70px;
  opacity: 0.35;
  pointer-events: none;
  z-index: 0;
}

/* ponto pulsante marcando "Amazônia" no planeta estilizado */
.stApp::after {
  content: "";
  position: fixed;
  top: 17%;
  right: 15%;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #baffd8;
  box-shadow: 0 0 0 0 rgba(186, 255, 216, 0.6);
  animation: dg-pulse 2.4s ease-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes dg-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(186, 255, 216, 0.55); }
  70%  { box-shadow: 0 0 0 18px rgba(186, 255, 216, 0); }
  100% { box-shadow: 0 0 0 0 rgba(186, 255, 216, 0); }
}

/* cartão claro por trás do conteúdo, pra garantir leitura */
.block-container {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  padding: 2.2rem 2.4rem 2.6rem 2.4rem;
  margin-top: 1.2rem;
  box-shadow: 0 12px 45px rgba(2, 10, 25, 0.45);
}

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #08213f 0%, #0a2a52 100%);
}
section[data-testid="stSidebar"] * {
  color: #eaf6f0 !important;
}
</style>
"""
