<script setup>
import { useHead } from '@vueuse/head'
import { RouterLink } from 'vue-router'
import { ref } from 'vue';


useHead({
  title: "The Books Club - Un Blog per Tutti",
  htmlAttrs: {
    lang: 'it',
  },
  meta: [
    {
      name: "description",
      content: "Benvenuto su The Books Club, la nuova piattaforma user friendly dove puoi parlare di ciò che ti piace."
    }
  ],
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/it"
    },
    {
      rel: "alternate",
      hreflang: "en",
      href: "https://thebooksclub.com/en"
    },
    {
      rel: "alternate",
      hreflang: "it",
      href: "https://thebooksclub.com/it"
    },
    {
      rel: "alternate",
      hreflang: "de",
      href: "https://thebooksclub.com/de"
    },
    {
      rel: "alternate",
      hreflang: "es",
      href: "https://thebooksclub.com/es"
    },
    {
      rel: "alternate",
      hreflang: "fr",
      href: "https://thebooksclub.com/fr"
    },
    {
      rel: "alternate",
      hreflang: "x-default",
      href: "https://thebooksclub.com/en"
    },
    {
      rel: "icon",
      href: "https://thebooksclub.com/favicon.ico",
      sizes:"any"
    }
  ]
})


const showRes1 = ref(false)
const toggleRes1 = () => { showRes1.value = !showRes1.value }

const showRes2 = ref(false)
const toggleRes2 = () => { showRes2.value = !showRes2.value }

const showRes3 = ref(false)
const toggleRes3 = () => { showRes3.value = !showRes3.value }


const showRes4 = ref(false)
const toggleRes4 = () => { showRes4.value = !showRes4.value }


const showRes5 = ref(false)
const toggleRes5 = () => { showRes5.value = !showRes5.value }

const showRes6 = ref(false)
const toggleRes6 = () => { showRes6.value = !showRes6.value }

const showRes7 = ref(false)
const toggleRes7 = () => { showRes7.value = !showRes7.value }


const showRes8 = ref(false)
const toggleRes8 = () => { showRes8.value = !showRes8.value }


const showRes9 = ref(false)
const toggleRes9 = () => { showRes9.value = !showRes9.value }

</script>




<template>
  <div class="container-fluid mt-3 mx-0 px-0">
    <h1 class="text-warning fw-bold text-center">Benvenuto su The Books Club</h1>
    
    <p class="text-center mt-4 p-outside">Siamo contenti che finalmente tu ci abbia raggiunto sul nostro sito.<br>In questa pagina troverai una breve descrizione del progetto e delle sue funzionalità, se sei interessato per favore continua a leggere.<br>D'altra parte se ci conosci già o sei già convinto, puoi anche procedere direttamente alla <RouterLink to="/registration" style="color:#ffc107; font-weight: bold; text-decoration:none;">Registrazione</RouterLink> o al <RouterLink to="/login" style="color:#ffc107; font-weight: bold; text-decoration:none;">Login</RouterLink>, la scelta è tua.</p>
    
    <p class="text-center mt-4 p-outside">In poche parole questa piattaforma è un social network dove ognuno può parlare liberamente di ciò che più gli interessa.<br>E' stato inizialmente pensato per gli amanti della letteratura, per dare loro un luogo dove possano parlare dei loro libri preferiti.<br>Noi pensiamo davvero che questo passatempo (il passatempo di leggere) possa contribuire a creare persone migliori e quindi anche un mondo migliore, in generale.<br>Ma questo progetto non riguarda soltanto i libri.<br>Abbiamo applicato la stessa idea a diverse categorie, questo ha portato alla attuale struttura della applicazione.</p>
    
    <p class="text-center mt-4 p-outside">Come puoi vedere ci sono diverse sezioni, divise per argomento, dove puoi indirizzare i tuoi Post.<br>Assegnando un Post and una certa categoria stiamo di fatto dicendo che deve essere mostrato nella sezione corrispondente a quella categoria.<br>Tutti i Post, indipendentemente dalla categoria, saranno mostrati nella Home, quindi frequentando la Home, potrai vedere tutti i post pubblici.<br>Creando un post, puoi anche assegnarlo alla categoria "Personale", così facendo verrà mostrato soltanto nella tua pagina del profilo.<br>Ci auguriamo che questa struttura possa agevolare gli utenti a concentrarsi su ciò che piace loro e su ciò che davvero vogliono da un social network, facilitando un ambiente positivo per le interazioni.</p>
    
    <p class="text-center mt-4 p-outside">La nostra idea è di dare agli utenti un posto dove possano confrontarsi liberamente senza la preoccupazione di sentirsi esposti pubblicamente.<br>Pensiamo che la struttura di questo progetto possa portare a questo risultato.<br>Uno dei nostri punti di focus è la privacy degli utenti, come speriamo tu possa notare usando l'applicazione.<br>Non ti verrà mai chiesto di condividere informazioni personali.<br>Avremo bisogno soltanto di un username e un indirizzo email per completare il processo di registrazione.<br>Puoi completare il tuo profilo utente fornendo le tue informazioni, sulla tua pagina del profilo, ma solo se vuoi e se credi che sia appropriato.</p>
    
    <p class="text-center mt-4 p-outside">Una cosa di cui dovresti essere al corrente è che, dato che non chiederemo autorizzazioni sulle funzionalità del tuo dispositivo, quando l'applicazione è chiusa non sarai in grado di ricevere notifiche.<br>Sappiamo che questo potrebbe non piacere ad alcuni utenti, ma in prospettiva, preferiamo questo approccio.<br>Vorremo che gli utenti venissero in questa piattaforma perchè sanno che qua possono divertirsi, e non per altre ragioni.</p>
    
    <div class="separator separator-class d-flex align-items-center justify-content-center text-danger gap-3">
      <div class="flex-grow-1 border-top border-danger"></div>
        <span class="text-center ">FAQ</span>
      <div class="flex-grow-1 border-top border-danger"></div>
    </div>
    
    <p class="text-center mt-4 p-outside">Qui puoi trovare le risposte alle domande principali che un utente potrebbe avere:</p>
    
    <ul>
      <li class="p-outside text-warning" @click="toggleRes1" style="cursor: pointer;">E' gratis?</li>
      <p v-show="showRes1" class="mt-2 p-outside">Al momento tutte le funzionalità sono gratis.<br>Stiamo pianificando di aggiungere un abbonamente per il servizio di chat, il prezzo sarà di 0.99€ al mese, tasse escluse.<br>Gli utenti saranno avvertiti una volta che l'abbonamento sarà stato introdotto.</p>
      
      <li class="p-outside text-warning" @click="toggleRes2" style="cursor: pointer;">Mi serve un account per guardare i contenuti?</li>
      <p v-show="showRes2" class="mt-2 p-outside">Al momento, non è necessario essere iscritti per vedere i contenuti.<br>Il materiale pubblico può essere visualizzato anche da utenti che non hanno fatto accesso.<br>Potremmo modificare questa policy se ci accorgiamo che danneggia la community.</p>
      
      <li class="p-outside text-warning" @click="toggleRes3" style="cursor: pointer;">Il mio profilo è pubblico o privato?</li>
      <p v-show="showRes3" class="mt-2 p-outside">Al momento tutti gli utenti sono pubblici, dato che non abbiamo implementato lo stato di account privato.<br>Potremmo considerare di aggiungere questa funzionalità in futuro.<br>Se vuoi temporaneamente nascondere il tuo account, puoi sospenderlo dalla tua pagina del profilo, in modalità "edit".<br>La modalità "edit" può essere attivata cliccando il pulsante "..." vicino al tuo nome utente nella tua pagina del profilo.<br>Una volta che il tuo utente è sospeso il tuo contenuto non sarà visibile per nessuno, fino alla riattivazione.<br>Puoi bloccare un utente specifico, dall'interagire con te, dalla sua pagina del profilo.</p>
      
      <li class="p-outside text-warning" @click="toggleRes4" style="cursor: pointer;">Posso eliminare il mio account?</li>
      <p v-show="showRes4" class="mt-2 p-outside">Si, l'account può essere eliminato e il processo è molto semplice.<br>Devi solo andare nella tua pagina del profilo, in modalità "edit", cliccare sul pulsante "Elimina Account" e seguire la procedura.<br>Se ti servono più informazioni puoi dare un'occhiata ai <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Termini di Utilizzo</a> per una checklist più completa.</p>
      
      <li class="p-outside text-warning" @click="toggleRes5" style="cursor: pointer;">Come viene gestita la privacy?</li>
      <p v-show="showRes5" class="mt-2 p-outside">La risposta breve è: non scambiamo informazioni con terze parti ed usiamo solo cookie tecnici essenziali, strettamente necessari al funzionamento della nostra applicazione.<br>Se ti servono più dettagli puoi dare un'occhiata alla <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">Policy sulla Privacy</a></p>
      
      <li class="p-outside text-warning" @click="toggleRes6" style="cursor: pointer;">La piattaforma può essere usata da account business?</li>
      <p v-show="showRes6" class="mt-2 p-outside">Al momento, la piattaforma è aperta soltanto ad utenti normali.<br>Per aziende offriamo un servizio di spazi pubblicitari su questa piattaforma che è completamente gestito da noi e non coinvolge terze parti.<br>Se ti servono più informazioni puoi visitare questa pagina <RouterLink to="/info-contacts" style="color:#ffc107; font-weight: bold; text-decoration:none;">Informazioni e Contatti</RouterLink> o contattarci a questo indirizzo email: <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span></p>
      
      <li class="p-outside text-warning" @click="toggleRes7" style="cursor: pointer;">Come funziona la moderazione dei contenuti?</li>
      <p v-show="showRes7" class="mt-2 p-outside">Data la nostra  resposabilità verso gli utenti, per mantenere un ambiente sano, per noi è necessario moderare i contenuti.<br>La moderazione dei file, come immagini e video è fatta principalmente da un algoritmo di Machine Learning.<br>Riguardo al contenuto scritto, monitoriamo l'applicazione costantemente. Per entrambi contiamo sul supporto degli utenti.<br>Se ti capita di notare contenuto non in linea con la policy, descritta nei <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Termini di Utilizzo</a>, o vuoi segnalare un comportamento scorretto o dannoso per favore contattaci a questa email: <span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span> allegando uno screenshot, responderemo in tempi brevi.</p>
      
      <li class="p-outside text-warning" @click="toggleRes8" style="cursor: pointer;">Posso postare in più lingue?</li>
      <p v-show="showRes8" class="mt-2 p-outside">Si, puoi postare in più lingue.<br>Per cambiare il linguaggio dell'applicazione basta cliccare sul pulsante a forma di globo, che puoi trovare in ogni pagina, e scegliere il linguaggio che desideri.<br>Postando in una certa lingua il tuo Post sarà visibile solo in quella lingua, non sarà tradotto automaticamente nelle altre.<br>Quindi se desideri avere lo stesso Post in più lingue, dovrai farlo per tutte le lingue indipendentemente.</p>
      
      <li class="p-outside text-warning" @click="toggleRes9" style="cursor: pointer;">Come funzionano le notifiche?</li>
      <p v-show="showRes9" class="mt-2 p-outside">Come già anticipato, dato che non chiederemo autorizzazioni per le notifiche sul tuo dispositivo, non potrai ricevere notifiche quando l'applicaione è chiusa.<br>Tuttavia, appena effettuerai l'accesso, le notifiche riguardanti commenti, menzioni o messaggi che hai ricevuto saranno mostrate sui due pulsanti nella barra di navigazione in cima alla pagina.<br>Cliccando su una notifica (ad esempio una risposta ad un commento) l'applicazione ti porterà direttamente all'oggetto della notifica.</p>
      
    </ul>
    
    <p class="text-center mt-4 p-outside mb-5">Hai ancora domande o desideri contattarci per un'altra ragione?<br>Puoi scriverci una mail a: <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>. Saremo felici di aiutare.</p>
      
  </div>
</template>
