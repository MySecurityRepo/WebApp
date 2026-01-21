<script setup>
import { useHead } from '@vueuse/head'
import { RouterLink } from 'vue-router'
import { ref } from 'vue';


useHead({
  title: "The Books Club - Un Blog Para Todos",
  htmlAttrs: {
    lang: 'es',
  },
  meta: [
    {
      name: "description",
      content: "Bienvenido a The Books Club, la nueva plataforma fácil de usar donde puedes hablar de lo que te gusta."
    }
  ],
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/es"
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
    <h1 class="text-warning fw-bold text-center">Bienvenido a The Books Club</h1>
    
    <p class="text-center mt-4 p-outside">Nos alegra que por fin te hayas unido a nuestro sitio.<br>En esta página encontrarás una breve descripción del proyecto y de sus funciones; si te interesa, por favor sigue leyendo.<br>Por otra parte, si ya nos conoces o ya estás convencido, también puedes proceder directamente al <RouterLink to="/registration" style="color:#ffc107; font-weight: bold; text-decoration:none;">Registro</RouterLink> o al  <RouterLink to="/login" style="color:#ffc107; font-weight: bold; text-decoration:none;">Login</RouterLink>, la elección es tuya.</p>
    
    <p class="text-center mt-4 p-outside">En pocas palabras, esta plataforma es una red social donde las personas pueden hablar libremente de las cosas que les gustan.<br>Fue pensado inicialmente para los amantes de la literatura, para darles un lugar donde puedan hablar de sus libros favoritos.<br>Realmente creemos que este pasatiempo (el pasatiempo de leer) puede contribuir a formar personas mejores y, por lo tanto, también un mundo mejor, en general.<br>Pero este proyecto no trata solamente de los libros.<br>Hemos aplicado la misma idea a varias categorías, y esto ha dado lugar a la estructura actual de la aplicación.</p>
    
    <p class="text-center mt-4 p-outside">Como puedes ver, hay varias secciones divididas por tema, donde puedes dirigir tus Publicaciones.<br>Al asignar una Publicación a una cierta categoría, de hecho estamos diciendo que debe mostrarse en la sección correspondiente a esa categoría.<br>Todas las Publicaciones, independientemente de la categoría, se mostrarán en la Inicio, así que, visitando la Inicio, podrás ver todas las publicaciones públicas.<br>Al crear una publicación, también puedes asignarla a la categoría “Personal”; haciéndolo así, se mostrará únicamente en tu página de perfil.<br>Esperamos que esta estructura pueda ayudar a los usuarios a concentrarse en lo que les gusta y en lo que realmente quieren de una red social, facilitando un entorno positivo para las interacciones.</p>
    
    <p class="text-center mt-4 p-outside">Nuestra idea es dar a los usuarios un lugar donde puedan intercambiar libremente sin la preocupación de sentirse expuestos públicamente.<br>Creemos que la estructura de este proyecto puede llevar a este resultado.<br>Uno de nuestros puntos de enfoque es la privacidad de los usuarios, como esperamos que puedas notar al usar la aplicación.<br>Nunca se te pedirá que compartas información personal.<br>Solo necesitaremos un nombre de usuario y una dirección de correo electrónico para completar el proceso de registro.<br>Puedes completar tu perfil de usuario proporcionando tu información en tu página de perfil, pero solo si quieres y si consideras que es apropiado.</p>
    
    <p class="text-center mt-4 p-outside">Una cosa de la que deberías estar al tanto es que, dado que no pediremos permisos sobre las funciones de tu dispositivo, cuando la aplicación esté cerrada no podrás recibir notificaciones.<br>abemos que esto podría no gustar a algún usuario, pero en perspectiva preferimos este enfoque.<br>Queremos que los usuarios vengan a esta plataforma porque saben que aquí pueden divertirse, y no por otras razones.</p>
    
    <div class="separator separator-class d-flex align-items-center justify-content-center text-danger gap-3">
      <div class="flex-grow-1 border-top border-danger"></div>
        <span class="text-center ">FAQ</span>
      <div class="flex-grow-1 border-top border-danger"></div>
    </div>
    
    <p class="text-center mt-4 p-outside">Aquí puedes encontrar las respuestas a las preguntas principales que un usuario podría tener:</p>
    
    <ul>
      <li class="p-outside text-warning" @click="toggleRes1" style="cursor: pointer;">¿Es gratis?</li>
      <p v-show="showRes1" class="mt-2 p-outside">Por el momento, todas las funcionalidades son gratuitas.<br>Estamos planeando añadir una suscripción para el servicio de chat; el precio será de 0,99 € al mes, impuestos no incluidos.<br>Los usuarios serán avisados una vez que la suscripción haya sido introducida.</p>
      
      <li class="p-outside text-warning" @click="toggleRes2" style="cursor: pointer;">¿Necesito una cuenta para ver los contenidos?</li>
      <p v-show="showRes2" class="mt-2 p-outside">Por el momento, no es necesario estar registrado para ver los contenidos.<br>El material público puede ser visualizado también por usuarios que no han iniciado sesión.<br>Podríamos modificar esta política si nos damos cuenta de que perjudica a la comunidad.</p>
      
      <li class="p-outside text-warning" @click="toggleRes3" style="cursor: pointer;">¿Mi perfil es público o privado?</li>
      <p v-show="showRes3" class="mt-2 p-outside">Por el momento, todos los usuarios son públicos, ya que no hemos implementado el estado de cuenta privada.<br>Podríamos considerar añadir esta funcionalidad en el futuro.<br>Si quieres ocultar temporalmente tu cuenta, puedes suspenderla desde tu página de perfil, en el modo de “edición”.<br>El modo “edición” puede activarse haciendo clic en el botón “...” junto a tu nombre de usuario en tu página de perfil.<br>Una vez que tu cuenta esté suspendida, tu contenido no será visible para nadie hasta su reactivación.<br>Puedes bloquear a un usuario específico para que no interactúe contigo, desde su página de perfil.</p>
      
      <li class="p-outside text-warning" @click="toggleRes4" style="cursor: pointer;">¿Puedo eliminar mi cuenta?</li>
      <p v-show="showRes4" class="mt-2 p-outside">Sí, la cuenta puede eliminarse y el proceso es muy sencillo.<br>Solo tienes que ir a tu página de perfil, en modo “edición”, hacer clic en el botón “Eliminar cuenta” y seguir el procedimiento.<br>Si necesitas más información, puedes echar un vistazo a los <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Términos de Uso</a> para una lista de verificación más completa.</p>
      
      <li class="p-outside text-warning" @click="toggleRes5" style="cursor: pointer;">¿Cómo se gestiona la privacidad?</li>
      <p v-show="showRes5" class="mt-2 p-outside">La respuesta breve es: no intercambiamos información con terceros y usamos solo cookies técnicas esenciales, estrictamente necesarias para el funcionamiento de nuestra aplicación.<br>Si quieres más detalles, puedes echar un vistazo a la <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">Política de Privacidad</a></p>
      
      <li class="p-outside text-warning" @click="toggleRes6" style="cursor: pointer;">¿La plataforma puede ser utilizada por cuentas empresariales?</li>
      <p v-show="showRes6" class="mt-2 p-outside">Por el momento, la plataforma está abierta únicamente a usuarios normales.<br>Para las empresas ofrecemos un servicio de espacios publicitarios en esta plataforma, que está completamente gestionado por nosotros y no implica a terceros.<br>Si quieres más información, puedes visitar esta página <RouterLink to="/info-contacts" style="color:#ffc107; font-weight: bold; text-decoration:none;">Información y Contactos</RouterLink> o contactarnos a esta dirección de correo: <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span></p>
      
      <li class="p-outside text-warning" @click="toggleRes7" style="cursor: pointer;">¿Cómo funciona la moderación de los contenidos?</li>
      <p v-show="showRes7" class="mt-2 p-outside">Dada nuestra responsabilidad hacia los usuarios, para mantener un entorno sano, para nosotros es necesario moderar los contenidos.<br>La moderación de los archivos, como imágenes y vídeos, se realiza principalmente mediante un algoritmo de aprendizaje automático.<br>Con respecto al contenido escrito, monitorizamos la aplicación constantemente. Para ambos casos contamos con el apoyo de los usuarios.<br>Si te ocurre notar contenido que no esté en línea con la política descrita en los <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Términos de Uso</a>, o quieres informar de un comportamiento incorrecto o dañino, por favor contáctanos a este correo: <span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span> adjuntando una captura de pantalla; responderemos en un corto plazo.</p>
      
      <li class="p-outside text-warning" @click="toggleRes8" style="cursor: pointer;">¿Puedo publicar en varios idiomas?</li>
      <p v-show="showRes8" class="mt-2 p-outside">Sí, puedes publicar en varios idiomas.<br>Para cambiar el idioma de la aplicación, basta con hacer clic en el botón con forma de globo, que puedes encontrar en cada página, y elegir el idioma que desees.<br>Publicando en un determinado idioma, tu Publicación será visible solo en ese idioma; no será traducida automáticamente a los demás.<br>Así que, si deseas tener la misma Publicación en varios idiomas, tendrás que crearla por separado para cada idioma.</p>
      
      <li class="p-outside text-warning" @click="toggleRes9" style="cursor: pointer;">¿Cómo funcionan las notificaciones?</li>
      <p v-show="showRes9" class="mt-2 p-outside">Como ya se adelantó, dado que no pediremos permisos de notificaciones en tu dispositivo, no podrás recibir notificaciones cuando la aplicación esté cerrada.<br>Sin embargo, en cuanto inicies sesión, las notificaciones sobre comentarios, menciones o mensajes que hayas recibido se mostrarán en los dos botones de la barra de navegación en la parte superior de la página.<br>Al hacer clic en una notificación (por ejemplo, una respuesta a un comentario), la aplicación te llevará directamente al objeto de la notificación.</p>
      
    </ul>
    
    <p class="text-center mt-4 p-outside mb-5">¿Tienes más preguntas o deseas contactarnos por otra razón?<br>Puedes escribirnos un correo a: <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>. Estaremos encantados de ayudarte.</p>
      
  </div>
</template>
