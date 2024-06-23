# Sofware deepsleep for Raspberry Pi Pico and RP2040 chip
# La funzione di deepsleep non è integrata lato hardware (è presente invece nei microntrollori del tipo ESP32)
# La funzione deepsleep sebbene non prevista da RB Pico è comunque disponibile su Micropython: la sua implementazione generica però sembra causare un errore 
# abbastanza frequente (circa 1/25 chiamate) per il quale RB Pico 'non si sveglia' al termine del tempo di deepsleep -> rimane in una fase di stallo
# Per tale motivo è stata necessaria un'implementazione alternativa
#
# Implementazione di deepsleep prevede l'underclock del processore RP2040 passando da 120MHz a 40MHz e eliminando l'alimentazione a 25 su 30 pin
# GPIO non disconnessi sono:
#           - GPIO25 collegato al LED integrato
#           - GPIO14 responsabile comunicazione protocollo UART
#           - GPIO15 responsabile comunicazione protocollo UART
# NB: ulteriori GPIO potrebbero non dover essere disconnessi nel caso RB utilizzi tali pin -> comportamento di RB da testare
#       es. GPIO0 e GPIO1 responsabili comunicazione protocollo SPI
#
# Il tempo di deepsleep viene implementato tramite la funzione sleep(sec) del modulo integrato 'time': 
# per intervalli di sleep molto elevati (t > 20-25min) si consiglia di suddividere il tempo di sleep in 'frazioni di tempo' minori
# attraverso un maggior numero di chiamate alla funzione sleep -> funzionalità implementata con la funzione delay (stesso problema riscontrato con deepsleep)
#       es. deepsleep di 1h (3600s) si divide 3600 in 60 chiamate sleep() di 60s 
#
# ANALISI PRESTAZIONI: 
# Sebbene tale funzionalià sia ancora da testare su diversi dispositivi e in condizioni differenti, un primo test preleminare ha evidenziato come durante il periodo 
# di deepsleep il microcontrollore riduca notevolmente il suo assorbimento in corrente -> in media 0.005A a 5V in confronto ai 0.030-0.020A a 5V della funzione integrata.
# Rispetto all'implementazione di Micropython ad una prima analisi sembra che questa implementazione sia migliore in termini di prestazioni energetiche: si passa infatti da
# da 0.020-0.010A a 0.005A di media a 5V
#
# Il calo dell'assorbimento in corrente sembra essere dovuto principalmente alla rimozione dell'alimentazione alle GPIO (più di 10mA) piuttosto che all'underclock del processore:
# si deve però considerare che il valore scelto dell'underclock è comunque ben oltre la soglia minima impostabile (circa 18MHz) per sicurezza evitando possibili errori generati
# un troppo aggressivo underclock -> non ci dovrebbe comunque essere nessun tipo di problema nemmeno a valori più bassi
#
# NB: RB Pico fa affidamento sul suo clock interno per l'utilizzo di periferiche esterne, timers e UARTs: nel caso di uso dei tali durante underclock potrebbe rendere necessario
# un aggiustamento delle periferiche per garantire una corrette sincronizzazione -> non è detto che accada, va testato ma è bene tenerne conto
#
# BONUS: 
# Si potrebbe aggiungere un hard-reset del microcontrollore alla fine del deepsleep tramite funzione machine.reset()

from machine import Pin, freq
from time import sleep

def delay(seconds):
    seconds = seconds / 60
    for _ in range(seconds):
        sleep(60)
        print("sleeping!")

def gosleep():
    clock_speed = 48000000
    freq(clock_speed)
    
    for i in range(28):
        if i not in [25, 14, 15]:  # Alcuni GPIO sono usati, come il LED integrato
            gpio = Pin(i, Pin.IN, Pin.PULL_DOWN)

def wakeup():
    clock_speed = 125000000
    freq(clock_speed)

    for i in range(28):
        if i not in [25, 14, 15]:  # Alcuni GPIO sono usati, come il LED integrato
            gpio = Pin(i, Pin.OUT, Pin.PULL_DOWN)
            
    print("all up after sleep!")

def deepsleep(seconds):

    print("all down before sleep!")
    gosleep()
    sleep(0.1)
    
    print("going to sleep!")

    delay(seconds)

    print("waking up!")
    wakeup()
    sleep(0.1)

    
deepsleep(3600)
