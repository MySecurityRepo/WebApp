<script setup>
import { useHead } from '@vueuse/head'
import { RouterLink } from 'vue-router'
import { ref } from 'vue';


useHead({
  title: "The Books Club - Ein Blog für Alle",
  htmlAttrs: {
    lang: 'de',
  },
  meta: [
    {
      name: "description",
      content: "Willkommen bei The Books Club, der neuen benutzerfreundlichen Plattform, auf der du über das sprechen kannst, was dir gefällt."
    }
  ],
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/de"
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
    <h1 class="text-warning fw-bold text-center">Willkommen bei The Books Club</h1>
    
    <p class="text-center mt-4 p-outside">Wir freuen uns, dass du endlich auf unserer Seite angekommen bist.<br>Auf dieser Seite findest du eine kurze Beschreibung des Projekts und seiner Funktionen; wenn du interessiert bist, lies bitte weiter.<br>Andererseits, wenn du uns bereits kennst oder schon überzeugt bist, kannst du auch direkt zur <RouterLink to="/registration" style="color:#ffc107; font-weight: bold; text-decoration:none;">Registrierung</RouterLink> oder zum <RouterLink to="/login" style="color:#ffc107; font-weight: bold; text-decoration:none;">Login</RouterLink> weitergehen, die Entscheidung liegt bei dir.</p>
    
    <p class="text-center mt-4 p-outside">Kurz gesagt ist diese Plattform ein soziales Netzwerk, in dem Menschen frei über die Dinge sprechen können, die ihnen gefallen.<br>Ursprünglich wurde sie für Literaturbegeisterte gedacht, um ihnen einen Ort zu bieten, an dem sie über ihre Lieblingsbücher sprechen können.<br>Wir glauben wirklich, dass dieses Hobby (das Lesen) dazu beitragen kann, bessere Menschen zu formen und damit insgesamt auch eine bessere Welt.<br>Aber dieses Projekt betrifft nicht nur Bücher.<br>Wir haben dieselbe Idee auf verschiedene Kategorien angewendet, was zur aktuellen Struktur der Anwendung geführt hat.</p>
    
    <p class="text-center mt-4 p-outside">Wie du sehen kannst, gibt es verschiedene Bereiche, nach Themen unterteilt, in denen du deine Posts einordnen kannst.<br>Indem wir einem Post eine bestimmte Kategorie zuweisen, sagen wir praktisch, dass er im Bereich angezeigt werden soll, der dieser Kategorie entspricht.<br>Alle Posts, unabhängig von der Kategorie, werden auf der Startseite angezeigt; daher kannst du, indem du die Startseite besuchst, alle öffentlichen Posts sehen.<br>Wenn du einen Post erstellst, kannst du ihn auch der Kategorie „Persönlich“ zuweisen; dadurch wird er nur auf deiner Profilseite angezeigt.<br>Wir hoffen, dass diese Struktur den Nutzern dabei helfen kann, sich auf das zu konzentrieren, was ihnen gefällt und was sie wirklich von einem sozialen Netzwerk erwarten, und dass sie ein positives Umfeld für Interaktionen erleichtert.</p>
    
    <p class="text-center mt-4 p-outside">Unsere Idee ist es, den Nutzern einen Ort zu geben, an dem sie sich frei austauschen können, ohne die Sorge, sich öffentlich exponiert zu fühlen.<br>Wir glauben, dass die Struktur dieses Projekts zu diesem Ergebnis führen kann.<br>Einer unserer Schwerpunkte ist die Privatsphäre der Nutzer, wie du hoffentlich beim Verwenden der Anwendung bemerken wirst.<br>Du wirst niemals aufgefordert werden, persönliche Informationen preiszugeben.<br>Wir benötigen nur einen Benutzernamen und eine E-Mail-Adresse, um den Registrierungsprozess abzuschließen.<br>Du kannst dein Benutzerprofil vervollständigen, indem du deine Informationen auf deiner Profilseite angibst, aber nur, wenn du es möchtest und es für angemessen hältst.</p>
    
    <p class="text-center mt-4 p-outside">Etwas, dessen du dir bewusst sein solltest, ist, dass du keine Benachrichtigungen erhalten kannst, wenn die Anwendung geschlossen ist, da wir keine Berechtigungen für die Funktionen deines Geräts anfordern.<br>Wir wissen, dass dies einigen Nutzern möglicherweise nicht gefällt, aber langfristig bevorzugen wir diesen Ansatz.<br>Wir möchten, dass die Nutzer auf diese Plattform kommen, weil sie wissen, dass sie sich hier amüsieren können – und nicht aus anderen Gründen.</p>
    
    <div class="separator separator-class d-flex align-items-center justify-content-center text-danger gap-3">
      <div class="flex-grow-1 border-top border-danger"></div>
        <span class="text-center ">FAQ</span>
      <div class="flex-grow-1 border-top border-danger"></div>
    </div>
    
    <p class="text-center mt-4 p-outside">Hier findest du die Antworten auf die wichtigsten Fragen, die ein Nutzer haben könnte:</p>
    
    <ul>
      <li class="p-outside text-warning" @click="toggleRes1" style="cursor: pointer;">Ist es kostenlos?</li>
      <p v-show="showRes1" class="mt-2 p-outside">Im Moment sind alle Funktionen kostenlos.<br>Wir planen, ein Abonnement für den Chat-Dienst hinzuzufügen; der Preis wird 0,99 € pro Monat betragen, ohne Steuern.<br> sobald das Abonnement eingeführt wurde.</p>
      
      <li class="p-outside text-warning" @click="toggleRes2" style="cursor: pointer;">Brauche ich ein Konto, um die Inhalte anzusehen?</li>
      <p v-show="showRes2" class="mt-2 p-outside">Im Moment ist es nicht erforderlich, registriert zu sein, um die Inhalte zu sehen.<br>Öffentliches Material kann auch von Nutzern angesehen werden, die sich nicht angemeldet haben.<br>Wir könnten diese Richtlinie ändern, wenn wir feststellen, dass sie der Community schadet.</p>
      
      <li class="p-outside text-warning" @click="toggleRes3" style="cursor: pointer;">Ist mein Profil öffentlich oder privat?</li>
      <p v-show="showRes3" class="mt-2 p-outside">Im Moment sind alle Nutzer öffentlich, da wir den Status eines privaten Kontos noch nicht implementiert haben.<br>Wir könnten in Betracht ziehen, diese Funktionalität in Zukunft hinzuzufügen.<br>Wenn du dein Konto vorübergehend verbergen möchtest, kannst du es über deine Profilseite im „Bearbeiten“-Modus suspendieren.<br>Der „Bearbeiten“-Modus kann aktiviert werden, indem du auf den „…“-Button neben deinem Benutzernamen auf deiner Profilseite klickst.<br>Sobald dein Konto suspendiert ist, wird dein Inhalt für niemanden sichtbar sein, bis du es wieder aktivierst.<br>Du kannst einen bestimmten Nutzer über seine Profilseite blockieren, damit er nicht mehr mit dir interagieren kann.</p>
      
      <li class="p-outside text-warning" @click="toggleRes4" style="cursor: pointer;">Kann ich mein Konto löschen?</li>
      <p v-show="showRes4" class="mt-2 p-outside">Ja, das Konto kann gelöscht werden, und der Vorgang ist sehr einfach.<br>Du musst nur auf deine Profilseite gehen, den „Bearbeiten“-Modus aktivieren, auf den Button „Konto löschen“ klicken und der Anleitung folgen.<br>Wenn du mehr Informationen brauchst, kannst du einen Blick in die <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Nutzungsbedingungen</a> werfen, um eine vollständigere Checkliste zu erhalten.</p>
      
      <li class="p-outside text-warning" @click="toggleRes5" style="cursor: pointer;">Wie wird die Privatsphäre gehandhabt?</li>
      <p v-show="showRes5" class="mt-2 p-outside">Die kurze Antwort lautet: Wir tauschen keine Informationen mit Dritten aus und verwenden nur essenzielle technische Cookies, die für den Betrieb unserer Anwendung unbedingt notwendig sind.<br>Wenn du mehr Details möchtest, kannst du einen Blick in die <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">Datenschutzrichtlinie</a> werfen.</p>
      
      <li class="p-outside text-warning" @click="toggleRes6" style="cursor: pointer;">Kann die Plattform von Business-Konten genutzt werden?</li>
      <p v-show="showRes6" class="mt-2 p-outside">Im Moment ist die Plattform nur für normale Nutzer geöffnet.<br>Für Unternehmen bieten wir einen Werbeflächen-Service auf dieser Plattform an, der vollständig von uns verwaltet wird und keine Drittanbieter einbezieht.<br>Wenn du mehr Informationen möchtest, kannst du diese Seite <RouterLink to="/info-contacts" style="color:#ffc107; font-weight: bold; text-decoration:none;">Informationen und Kontakte</RouterLink> besuchen oder uns unter dieser E-Mail-Adresse kontaktieren: <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span></p>
      
      <li class="p-outside text-warning" @click="toggleRes7" style="cursor: pointer;">Wie funktioniert die Moderation der Inhalte?</li>
      <p v-show="showRes7" class="mt-2 p-outside">Aufgrund unserer Verantwortung gegenüber den Nutzern ist es für uns notwendig, die Inhalte zu moderieren, um eine gesunde Umgebung zu erhalten.<br>Die Moderation von Dateien wie Bildern und Videos wird hauptsächlich von einem Machine-Learning-Algorithmus durchgeführt.<br>Was den schriftlichen Inhalt betrifft, überwachen wir die Anwendung ständig. In beiden Fällen zählen wir auf die Unterstützung der Nutzer.<br>Wenn dir Inhalte auffallen, die nicht mit der in den <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Nutzungsbedingungen</a> beschriebenen Richtlinie übereinstimmen, oder wenn du ein falsches oder schädliches Verhalten melden möchtest, kontaktiere uns bitte unter dieser E-Mail-Adresse: <span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span> und füge einen Screenshot bei. Wir werden zeitnah antworten.</p>
      
      <li class="p-outside text-warning" @click="toggleRes8" style="cursor: pointer;">Kann ich in mehreren Sprachen posten?</li>
      <p v-show="showRes8" class="mt-2 p-outside">Ja, du kannst in mehreren Sprachen posten.<br>Um die Sprache der Anwendung zu ändern, musst du einfach auf den globusförmigen Button klicken, den du auf jeder Seite findest, und die gewünschte Sprache auswählen.<br>Wenn du in einer bestimmten Sprache postest, wird dein Post nur in dieser Sprache sichtbar sein; er wird nicht automatisch in die anderen Sprachen übersetzt.<br>Wenn du also denselben Post in mehreren Sprachen haben möchtest, musst du ihn für jede Sprache separat erstellen.</p>
      
      <li class="p-outside text-warning" @click="toggleRes9" style="cursor: pointer;">Wie funktionieren die Benachrichtigungen?</li>
      <p v-show="showRes9" class="mt-2 p-outside">Wie bereits erwähnt, wirst du keine Benachrichtigungen erhalten können, wenn die Anwendung geschlossen ist, da wir keine Berechtigungen für Benachrichtigungen auf deinem Gerät anfordern.<br>Sobald du dich jedoch anmeldest, werden Benachrichtigungen über Kommentare, Erwähnungen oder Nachrichten, die du erhalten hast, auf den beiden Buttons in der Navigationsleiste oben auf der Seite angezeigt.<br>Wenn du auf eine Benachrichtigung klickst (zum Beispiel auf eine Antwort auf einen Kommentar), führt dich die Anwendung direkt zum entsprechenden Inhalt.</p>
      
    </ul>
    
    <p class="text-center mt-4 p-outside mb-5">Hast du noch Fragen oder möchtest du uns aus einem anderen Grund kontaktieren?<br>Du kannst uns eine E-Mail schreiben an: <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>. Wir helfen dir gerne weiter.</p>
      
  </div>
</template>
