from prometheus_client import Counter

users_total = Counter(
    "users_total",
    "Total de usuarios cadastrados"
)

drivers_total = Counter(
    "drivers_total",
    "Total de motoristas cadastrados"
)

passengers_total = Counter(
    "passengers_total",
    "Total de passageiros cadastrados"
)

password_reset_requests_total = Counter(
    "password_reset_requests_total",
    "Total de solicitacoes de redefinicao de senha"
)

google_logins_total = Counter(
    "google_logins_total",
    "Total de logins realizados com Google"
)

logouts_total = Counter(
    "logouts_total",
    "Total de logouts realizados"
)