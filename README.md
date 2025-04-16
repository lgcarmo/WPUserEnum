# WP User Enumeration Tool

Ferramenta em Python para enumeração de usuários em sites WordPress.  
Utiliza 7 métodos conhecidos para identificar nomes de usuário e expor potenciais vetores de ataque.

---

## ⚡ Funcionalidades

- 🔍 **7 técnicas de enumeração** baseadas no artigo da GoSecure
- 🌐 Suporte a proxy (`--proxy`)
- 📁 Suporte a lista de domínios (`--list`)
- 📬 Suporte a wordlist de usuários/emails (`--userlist`)
- 🌈 Saída colorida para facilitar a leitura
- ✅ Compatível com domínios `.com.br`, `.gov.br`, `.org.br` via `tldextract`

---

## 🧠 Métodos disponíveis

| ID  | Técnica                                              |
|-----|------------------------------------------------------|
| 1   | REST API pública `/wp-json/wp/v2/users`              |
| 2   | Redirecionamento via `?author=ID`                    |
| 3   | RSS Feed (`/feed/` com `<dc:creator>`)               |
| 4   | Busca com `@mention`                                 |
| 5   | Mensagens de erro no login (`wp-login.php`)          |
| 6   | Força bruta via XML-RPC (`wp.getUsersBlogs`)         |
| 7   | REST API com filtro `search=email` em `api.dominio`  |

---

## 🚀 Uso

```bash
python3 wp_user_enum.py -u https://site.com.br --method all --userlist users.txt
