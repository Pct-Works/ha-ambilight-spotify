# Ambilight Spotify

Sincroniza tus luces con el **color de énfasis de la portada** de lo que suena en Spotify (o en cualquier reproductor que exponga la carátula) en Home Assistant.

*Read in [English](README.md).*

- Funciona con cualquier `media_player` con `entity_picture`: [SpotifyPlus](https://github.com/thlucas1/homeassistantcomponent_spotifyplus), la integración Spotify de core, Plex, Music Assistant…
- Cuatro modos de color: **Vibrante**, **Pastel**, **Fiel a la portada** e **Intenso / Dramático**.
- Deslizadores de brillo y saturación mínimos; los cambios se aplican **al instante** a la canción que suena.
- Nunca genera un color negro o gris oscuro (suelo de brillo).
- Solo cambia las luces que **ya están encendidas** y **nunca toca su brillo**.
- Restricciones opcionales: solo para ciertas fuentes de reproducción (por ejemplo un dispositivo de Spotify Connect) y/o solo mientras una entidad esté encendida.
- **Color por defecto** opcional, que se restaura cuando la sincronización se detiene.
- Sin YAML ni helpers: todo se configura desde la interfaz.

## Instalación

### HACS (repositorio personalizado)

1. HACS → ⋮ → **Repositorios personalizados** → añade `https://github.com/Pct-Works/ha-ambilight-spotify` como **Integración**.
2. Instala **Ambilight Spotify** y reinicia Home Assistant.
3. **Ajustes → Dispositivos y servicios → Añadir integración → Ambilight Spotify**.

### Manual

Copia `custom_components/ambilight_spotify` en tu carpeta `config/custom_components` y reinicia.

## Configuración

**Paso 1 — Reproductor.** El reproductor cuya portada se sigue.

**Paso 2 — Luces y comportamiento** (editable después con **Configurar**):

| Opción | Descripción |
| --- | --- |
| Luces | Luces que reciben el color. |
| Solo para estas fuentes de reproducción | Opcional. Sincroniza solo si el atributo `source` del reproductor coincide (sin distinguir mayúsculas). Útil para ignorar la reproducción en otros dispositivos. |
| Solo mientras esta entidad esté encendida | Opcional. Por ejemplo `light.todas`. |
| Color por defecto | Opcional. Se aplica a las luces cuando la sincronización se detiene (interruptor apagado, reproducción parada, condiciones no cumplidas). Vacío = se deja el último color. |
| Transición | Segundos que tardan las luces en cambiar de color. |

## Entidades

Cada entrada crea un dispositivo con:

| Entidad | Función |
| --- | --- |
| `switch` **Ambilight** | Activa o desactiva la sincronización. |
| `select` **Modo de color** | Vibrante / Pastel / Fiel / Intenso. |
| `number` **Brillo mínimo** | Brillo objetivo del color (0–100 %). |
| `number` **Saturación mínima** | Saturación mínima para que un color de la portada sea candidato (0–100 %). |
| `sensor` **Color de énfasis** | Estado `#rrggbb`; atributos `rgb_color`, `hs_color`, `mode`. Úsalo para teñir dashboards o controlar otros dispositivos. |
| `binary_sensor` **Sincronizando** | Encendido mientras se controlan las luces (diagnóstico). |

## Servicio `ambilight_spotify.apply`

Reenvía a las luces el color actual (o el color por defecto si la sincronización no está activa). Los campos son opcionales:

- `entity_id` — aplicar a estas luces en vez de a las configuradas.
- `config_entry_id` — limitar a una entrada.

Así la lógica de escenas queda **fuera** de la integración. Ejemplo: al cambiar de escena, que solo sigan la música las luces de esa escena:

```yaml
automation:
  - alias: Reaplicar color a las luces indirectas al cambiar de escena
    triggers:
      - trigger: state
        entity_id: scene.ambiente
    actions:
      - action: ambilight_spotify.apply
        data:
          entity_id:
            - light.deskbar
            - light.wled
```

## Cómo funciona

1. Cuando cambia el estado, la fuente o la portada del reproductor, se descarga la portada una vez y se reduce a una paleta de 12 colores.
2. Se elige el mejor candidato por saturación × brillo × peso en la imagen, con una saturación mínima.
3. Se conservan el tono y la saturación y se recompone el color según el modo, con un brillo mínimo.
4. El color se envía a las luces encendidas (`light.turn_on` solo con `rgb_color`).

Cambiar el modo o los deslizadores reutiliza la paleta en caché: sin nueva descarga.

## Licencia

MIT
