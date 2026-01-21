<script setup>
import { useHead } from '@vueuse/head'
import { RouterLink } from 'vue-router'
import { ref } from 'vue';


useHead({
  title: "The Books Club - Un Blog pour Tous",
  htmlAttrs: {
    lang: 'fr',
  },
  meta: [
    {
      name: "description",
      content: "Bienvenue sur The Books Club, la nouvelle plateforme conviviale où tu peux parler de ce que tu aimes."
    }
  ],
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/fr"
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
    <h1 class="text-warning fw-bold text-center">Bienvenue sur The Books Club</h1>
    
    <p class="text-center mt-4 p-outside">Nous sommes ravis que tu nous aies enfin rejoints sur notre site.<br>Sur cette page, tu trouveras une brève description du projet et de ses fonctionnalités ; si cela t’intéresse, merci de continuer à lire.<br>D’un autre côté, si tu nous connais déjà ou si tu es déjà convaincu, tu peux aussi passer directement à l'<RouterLink to="/registration" style="color:#ffc107; font-weight: bold; text-decoration:none;">Inscription</RouterLink> ou à la <RouterLink to="/login" style="color:#ffc107; font-weight: bold; text-decoration:none;">Connexion</RouterLink>, le choix t’appartient.</p>
    
    <p class="text-center mt-4 p-outside">En quelques mots, cette plateforme est un réseau social où les personnes peuvent parler librement des choses qu’elles aiment.<br>Il a été conçu au départ pour les amateurs de littérature, afin de leur offrir un lieu où ils puissent parler de leurs livres préférés.<br>Nous pensons vraiment que ce passe-temps (le passe-temps de lire) peut contribuer à créer de meilleures personnes et donc aussi un monde meilleur, de manière générale.<br>Mais ce projet ne concerne pas seulement les livres.<br>Nous avons appliqué la même idée à plusieurs catégories, ce qui a conduit à la structure actuelle de l’application.</p>
    
    <p class="text-center mt-4 p-outside">Comme tu peux le voir, il y a plusieurs sections, réparties par sujet, où tu peux adresser tes Publications.<br>En assignant une Publication à une certaine catégorie, nous disons en fait qu’elle doit être affichée dans la section correspondant à cette catégorie.<br>Toutes les Publications, indépendamment de la catégorie, seront affichées dans l’Accueil ; donc en fréquentant l’Accueil, tu pourras voir toutes les publications publiques.<br>En créant une publication, tu peux aussi l’assigner à la catégorie “Personnel” ; en faisant cela, elle n’apparaîtra que sur ta page de profil.<br>Nous espérons que cette structure pourra aider les utilisateurs à se concentrer sur ce qu’ils aiment et sur ce qu’ils veulent réellement d’un réseau social, tout en facilitant un environnement positif pour les interactions.</p>
    
    <p class="text-center mt-4 p-outside">Notre idée est d’offrir aux utilisateurs un endroit où ils puissent échanger librement sans la préoccupation de se sentir exposés publiquement.<br>Nous pensons que la structure de ce projet peut conduire à ce résultat.<br>L’un de nos points d’attention est la confidentialité des utilisateurs, comme nous espérons que tu pourras le constater en utilisant l’application.<br>Il ne te sera jamais demandé de partager des informations personnelles.<br>Nous aurons seulement besoin d’un nom d’utilisateur et d’une adresse e-mail pour compléter le processus d’inscription.<br>Tu peux compléter ton profil utilisateur en fournissant tes informations sur ta page de profil, mais seulement si tu le veux et si tu estimes que c’est approprié.</p>
    
    <p class="text-center mt-4 p-outside">Une chose dont tu devrais être au courant est que, comme nous ne demanderons aucune autorisation concernant les fonctionnalités de ton appareil, lorsque l’application sera fermée tu ne pourras pas recevoir de notifications.<br>Nous savons que cela pourrait ne pas plaire à certains utilisateurs, mais avec du recul nous préférons cette approche.<br>Nous voudrions que les utilisateurs viennent sur cette plateforme parce qu’ils savent qu’ici ils peuvent s’amuser, et non pour d’autres raisons.</p>
    
    <div class="separator separator-class d-flex align-items-center justify-content-center text-danger gap-3">
      <div class="flex-grow-1 border-top border-danger"></div>
        <span class="text-center ">FAQ</span>
      <div class="flex-grow-1 border-top border-danger"></div>
    </div>
    
    <p class="text-center mt-4 p-outside">Ici, tu peux trouver les réponses aux principales questions qu’un utilisateur pourrait avoir :</p>
    
    <ul>
      <li class="p-outside text-warning" @click="toggleRes1" style="cursor: pointer;">Est-ce gratuit ?</li>
      <p v-show="showRes1" class="mt-2 p-outside">Pour le moment, toutes les fonctionnalités sont gratuites.<br>Nous prévoyons d’ajouter un abonnement pour le service de messagerie ; le prix sera de 0,99 € par mois, taxes non incluses.<br>Les utilisateurs seront avertis une fois que l’abonnement aura été introduit.</p>
      
      <li class="p-outside text-warning" @click="toggleRes2" style="cursor: pointer;">Ai-je besoin d’un compte pour consulter les contenus ?</li>
      <p v-show="showRes2" class="mt-2 p-outside">Pour le moment, il n’est pas nécessaire d’être inscrit pour consulter les contenus.<br>Le contenu public peut également être consulté par des utilisateurs qui ne se sont pas connectés.<br>Nous pourrions modifier cette politique si nous constatons qu’elle nuit à la communauté.</p>
      
      <li class="p-outside text-warning" @click="toggleRes3" style="cursor: pointer;">Mon profil est-il public ou privé ?</li>
      <p v-show="showRes3" class="mt-2 p-outside">Pour le moment, tous les utilisateurs sont publics, puisque nous n’avons pas encore implémenté le statut de compte privé.<br>Nous pourrions envisager d’ajouter cette fonctionnalité à l’avenir.<br>Si tu veux masquer temporairement ton compte, tu peux le suspendre depuis ta page de profil, en mode “édition”.<br>Le mode “édition” peut être activé en cliquant sur le bouton “…” à côté de ton nom d’utilisateur sur ta page de profil.<br>Une fois que ton compte est suspendu, ton contenu ne sera visible pour personne jusqu’à sa réactivation.<br>Tu peux bloquer un utilisateur spécifique pour l’empêcher d’interagir avec toi, depuis sa page de profil.</p>
      
      <li class="p-outside text-warning" @click="toggleRes4" style="cursor: pointer;">Puis-je supprimer mon compte ?</li>
      <p v-show="showRes4" class="mt-2 p-outside">Oui, le compte peut être supprimé et le processus est très simple.<br>Tu dois simplement aller sur ta page de profil, en mode “édition”, cliquer sur le bouton “Supprimer le compte” et suivre la procédure.<br>Si tu as besoin de plus d’informations, tu peux consulter les <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Conditions d’Utilisation</a> pour une liste de vérification plus complète.</p>
      
      <li class="p-outside text-warning" @click="toggleRes5" style="cursor: pointer;">Comment la confidentialité est-elle gérée ?</li>
      <p v-show="showRes5" class="mt-2 p-outside">La réponse courte est : nous n’échangeons aucune information avec des tiers et nous utilisons uniquement des cookies techniques essentiels, strictement nécessaires au fonctionnement de notre application.<br>Si tu veux plus de détails, tu peux consulter la <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">Politique de Confidentialité</a></p>
      
      <li class="p-outside text-warning" @click="toggleRes6" style="cursor: pointer;">La plateforme peut-elle être utilisée par des comptes professionnels ?</li>
      <p v-show="showRes6" class="mt-2 p-outside">Pour le moment, la plateforme est ouverte uniquement aux utilisateurs ordinaires.<br>Pour les entreprises, nous proposons un service d’espaces publicitaires sur cette plateforme, entièrement géré par nous et n’impliquant aucune tierce partie.<br>Si tu veux plus d’informations, tu peux visiter cette page <RouterLink to="/info-contacts" style="color:#ffc107; font-weight: bold; text-decoration:none;">Informations et Contacts</RouterLink> ou nous contacter à cette adresse e-mail : <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span></p>
      
      <li class="p-outside text-warning" @click="toggleRes7" style="cursor: pointer;">Comment fonctionne la modération des contenus ?</li>
      <p v-show="showRes7" class="mt-2 p-outside">Compte tenu de notre responsabilité envers les utilisateurs, afin de maintenir un environnement sain, il nous est nécessaire de modérer les contenus.<br>La modération des fichiers, comme les images et les vidéos, est effectuée principalement par un algorithme d’apprentissage automatique.<br>En ce qui concerne le contenu écrit, nous surveillons l’application en permanence. Pour les deux aspects, nous comptons sur le soutien des utilisateurs.<br>Si tu remarques un contenu qui n’est pas conforme à la politique décrite dans les <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Conditions d’Utilisation</a>, ou si tu souhaites signaler un comportement incorrect ou nuisible, merci de nous contacter à cet e-mail : <span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span> en joignant une capture d’écran ; nous te répondrons dans les plus brefs délais.</p>
      
      <li class="p-outside text-warning" @click="toggleRes8" style="cursor: pointer;">Puis-je publier dans plusieurs langues ?</li>
      <p v-show="showRes8" class="mt-2 p-outside">Oui, tu peux publier dans plusieurs langues.<br>Pour changer la langue de l’application, il suffit de cliquer sur le bouton en forme de globe, que tu peux trouver sur chaque page, et de choisir la langue que tu souhaites.<br>En publiant dans une certaine langue, ta Publication sera visible uniquement dans cette langue ; elle ne sera pas traduite automatiquement dans les autres.<br>Donc, si tu veux avoir la même Publication dans plusieurs langues, tu devras la créer séparément pour chacune d’elles.</p>
      
      <li class="p-outside text-warning" @click="toggleRes9" style="cursor: pointer;">Comment fonctionnent les notifications ?</li>
      <p v-show="showRes9" class="mt-2 p-outside">Comme indiqué précédemment, puisque nous ne demanderons pas d’autorisations de notifications sur ton appareil, tu ne pourras pas recevoir de notifications lorsque l’application sera fermée.<br>Cependant, dès que tu te connecteras, les notifications concernant les commentaires, les mentions ou les messages que tu as reçus apparaîtront sur les deux boutons de la barre de navigation en haut de la page.<br>En cliquant sur une notification (par exemple une réponse à un commentaire), l’application te conduira directement à l’objet de la notification.</p>
      
    </ul>
    
    <p class="text-center mt-4 p-outside mb-5">As-tu encore des questions ou souhaites-tu nous contacter pour une autre raison ?<br>Tu peux nous écrire un e-mail à : <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>. Nous serons ravis de t’aider.</p>
      
  </div>
</template>
