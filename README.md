# Hitachi airCloud Gateway para Home Assistant

Integração local para sistemas **VRF Hitachi** controlados pelo **airCloud Gateway (HC-IOTGW)**. Cada unidade interna vira uma entidade `climate` no Home Assistant, com ligar/desligar, modo, temperatura e ventilação, sem nuvem.

*English summary at the end.*

## Recursos

- Configuração pela interface (IP, usuário e senha do gateway)
- Descoberta automática das unidades internas
- Modos: Frio, Calor, Desumidificar, Ventilar e Desligado
- Ventilação: baixa, média, alta, máxima e automática
- Temperatura de 16 a 30 °C, em passos de 0,5 °C
- Relogin automático quando a sessão do gateway expira
- Comunicação 100% local (`local_polling`, a cada 30 s)

## Instalação

### HACS (repositório personalizado)

1. HACS → menu ⋮ → **Repositórios personalizados**
2. Cole `https://github.com/BRPRIM3/ha-hitachi-aircloud` e escolha a categoria **Integration**
3. Instale **Hitachi airCloud Gateway** e reinicie o Home Assistant

### Manual

Copie a pasta `custom_components/hitachi_aircloud` para `/config/custom_components/` e reinicie o Home Assistant.

## Configuração

Configurações → Dispositivos e serviços → **Adicionar integração** → *Hitachi airCloud Gateway*. Informe o IP do gateway e o mesmo usuário e senha da página web dele.

## Observações

- O equipamento leva de 10 a 60 segundos para refletir um comando. Nesse intervalo a integração mantém na tela o valor enviado.
- O gateway usa certificado autoassinado; a integração aceita esse certificado na rede local.
- Os bloqueios do controle remoto de parede não são alterados: o controle continua funcionando.

## Protocolo (referência)

Interface web local do gateway em `https://<ip>/index.cgi`:

| Ação | Requisição | Campos |
|---|---|---|
| Login | `POST ?mod=0&act=1` | `username`, `password` (sessão por cookie) |
| Status | `GET ?mod=3&act=35&dev=N` | Resposta JSON (`Operation`, `Mode`, `Tset`, `Ti`, `Real`, `Capacity`…) |
| Comando | `POST ?mod=3&act=33&dev=N` | `OnOff` (0/1), `OperationMode` (Cool=4, Heat=2, Fan=1, Dry=64), `FanSpeed` (0, 1, 2, 18, Auto=32), `SetTemp` |

Testado com um gateway HC-IOTGW e 8 unidades internas.

## Aviso

Desenvolvido por **JS Redes e Automação**. Licença MIT.

Projeto independente, sem vínculo com Hitachi, Bosch ou Johnson Controls. Use por sua conta e risco.

---

## English summary

Local Home Assistant integration for Hitachi VRF systems behind the **airCloud Gateway (HC-IOTGW)**. Each indoor unit becomes a `climate` entity (on/off, mode, target temperature, fan speed). Configure it from the UI with the gateway's IP, username and password. Install via HACS as a custom repository (category: Integration) or copy `custom_components/hitachi_aircloud` manually.
