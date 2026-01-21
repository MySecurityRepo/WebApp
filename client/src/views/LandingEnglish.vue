<script setup>
import { useHead } from '@vueuse/head'
import { RouterLink } from 'vue-router'
import { ref } from 'vue';


useHead({
  title: "The Books Club - A Blog for Everyone",
  htmlAttrs: {
    lang: 'en',
  },
  meta: [
    {
      name: "description",
      content: "Welcome on The Books Club, the new user friendly platform where you can freely talk about the things you like."
    }
  ],
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/en"
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
    <h1 class="text-warning fw-bold text-center">Welcome on The Books Club</h1>
    
    <p class="text-center mt-4 p-outside">We are glad that finally you have landed on our site.<br>In this page you will find a brief description of this project and its features, if you are interested please continue reading.<br>On the other hand if you know us already or you are already convinced, you can head right into the action and proceed to the <RouterLink to="/registration" style="color:#ffc107; font-weight: bold; text-decoration:none;">Registration</RouterLink> or to the <RouterLink to="/login" style="color:#ffc107; font-weight: bold; text-decoration:none;">Login</RouterLink>.</p>
    
    <p class="text-center mt-4 p-outside">In few words this platform is a social network where people can talk about whatever they like.<br>This project was initially thought for all the literature lovers, to give them a place where they could discuss about their favorite books.<br>We truly think that this wonderful hobby (the hobby of reading) can contribute to create better people and a better world, in general.<br>But this platform is not just about books.<br>We took further our original idea and applied to other categories, this has led to the current site structure.</p>
    
    <p class="text-center mt-4 p-outside">As you can see there are different sections, divided by topic, where you can direct you Posts.<br>Once you create a Post as belonging to a certain category, it will be displayed in that category section.<br>All the Posts, regardless of their category, will be displayed in the Home page, so you won't miss anything.<br>When creating a Post you can choose to make it Personal, that way it will be showed only in your Profile page.<br>We hope this structure will help our users focusing on what they really like and want from a social network, and that will facilitate a positive environment for people to interact with each other.</p>
    
    <p class="text-center mt-4 p-outside">Our idea is to give users a place where they can exchange ideas freely and without the worry to publicly expose themselves.<br>We think that the current project structure is what can lead to that result.<br>One of our main focus is the user privacy; as you will see proceeding using this platform.<br>You will be never asked to share any personal information.<br>We will ask just the username and your email address for registration.<br>You can costumize your profile giving information about yourself, in your profile page, but only if you want and you think is appropriate.</p>
    
    <p class="text-center mt-4 p-outside">Please keep in mind that, since we are not asking for any functionality permission on your device, you won't be able to receive notifications when the platform is closed.<br>We know that this may annoy some users but, in prospective, we prefer this way.<br>We would like users to come to our platform because they want to have a good time, and not for other reasons.</p>
    
    <div class="separator separator-class d-flex align-items-center justify-content-center text-danger gap-3">
      <div class="flex-grow-1 border-top border-danger"></div>
        <span class="text-center ">FAQ</span>
      <div class="flex-grow-1 border-top border-danger"></div>
    </div>
    
    <p class="text-center mt-4 p-outside">Here you can find the answers to the main questions a user might have when starting to use our platform.</p>
    
    <ul>
      <li class="p-outside text-warning" @click="toggleRes1" style="cursor: pointer;">Is it free to use?</li>
      <p v-show="showRes1" class="mt-2 p-outside">At the moment, all the platform functionalities are free.<br>It is planned to include a small subscription for the private chat service, the price will be 0.99€ per month, taxes excluded.<br>The users will be notified upon subscription introduction.</p>
      
      <li class="p-outside text-warning" @click="toggleRes2" style="cursor: pointer;">Do I need an account to explore content?</li>
      <p v-show="showRes2" class="mt-2 p-outside">You don't strictly need an account to explore content.<br>At the moment all public material can be viewed also by users who are not signed in.<br>We may change this policy if we notice that it's not healthy for the community.</p>
      
      <li class="p-outside text-warning" @click="toggleRes3" style="cursor: pointer;">Is my profile public or private?</li>
      <p v-show="showRes3" class="mt-2 p-outside">At the moment, user accounts are public, as we have not implemented a private account toggle.<br>We may consider to introduce private accounts functionality in the future.<br>If you want to hide your account temporarily you can suspend your user in your profile page, in edit mode.<br>Edit mode is activated clicking the "..." beside your username in the profile page.<br>When your user is suspended your content won't be available for anybody, until reactivation.<br>If you don't want to interact with a specific user anymore, you can block them on their profile page.</p>
      
      <li class="p-outside text-warning" @click="toggleRes4" style="cursor: pointer;">Can I delete my account?</li>
      <p v-show="showRes4" class="mt-2 p-outside">Yes you can delete your account, and the process is very straightforward.<br>You just need to go to your profile page, in edit mode, click the "Delete Account" button and follow the procedure.<br>If you want further information please look at the <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Terms of Service</a> for a more comprehensive checklist.</p>
      
      <li class="p-outside text-warning" @click="toggleRes5" style="cursor: pointer;">How does the platform handle privacy?</li>
      <p v-show="showRes5" class="mt-2 p-outside">The short answer is: we do not share user information with third parties and we use only essential cookies, strictly necessary for the application functionality.<br>If you want to have more details please take a look at the <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">Privacy Policy</a></p>
      
      <li class="p-outside text-warning" @click="toggleRes6" style="cursor: pointer;">Can businesses or creators use the platform?</li>
      <p v-show="showRes6" class="mt-2 p-outside">At the moment the platform is opened to normal users only.<br>For Businesses we provide an advertisement service that is completely self-hosted and doesn't involve third parties.<br>If you want more information please visit the <RouterLink to="/info-contacts" style="color:#ffc107; font-weight: bold; text-decoration:none;">Info and Contacts</RouterLink> page or contact us at <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span></p>
      
      <li class="p-outside text-warning" @click="toggleRes7" style="cursor: pointer;">How does content moderation work?</li>
      <p v-show="showRes7" class="mt-2 p-outside">Given our responsabilities towards users, to keep a safe environment is necessary for us to moderate content.<br>Media moderation is done primarily through the use of a Machine Learning algorithm.<br>Regarding written content we inspect our platform constantly. For both we also rely on users feedback.<br>If you notice content that is not in line with the policy as described in the <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Terms of Service</a>, or want to report dangerous or incorrect behavior please notify us at <span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span> attaching a screenshot, we will answer promptly.</p>
      
      <li class="p-outside text-warning" @click="toggleRes8" style="cursor: pointer;">Can I post in different languages?</li>
      <p v-show="showRes8" class="mt-2 p-outside">Yes you can post in several languages.<br>To change the application language just click on the globe button you can find in any page and choose the language you want.<br>Please note that when you Post in a language, your Post will be visible only on that language, it won't be translated automatically to other languages.<br>So, if for example you want a Post to appear in two different languages you would have to make it in both languages indipendently.</p>
      
      <li class="p-outside text-warning" @click="toggleRes9" style="cursor: pointer;">How do notifications work?</li>
      <p v-show="showRes9" class="mt-2 p-outside">As already mentioned, since we are not asking for permissions on your device, you won't receive notifications when the platform is closed.<br>However, as soon as you sign back in, notifications regarding comments, mentions, or messages you received will be displayed on the two buttons in the top bar.<br>If you click on a displayed notification (i.e. a reply to a comment) the platform will bring you directly to the object of the notification.</p>
      
    </ul>
    
    <p class="text-center mt-4 p-outside mb-5">Do you still have questions or want to contact us for another reason?<br>You can reach out at <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>. We will be happy to assist.</p>
      
  </div>
</template>
