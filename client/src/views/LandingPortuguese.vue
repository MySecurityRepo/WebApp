<script setup>
import { useHead } from '@vueuse/head'
import { RouterLink } from 'vue-router'
import { ref } from 'vue';


useHead({
  title: "The Books Club - Um Blog para Todos",
  htmlAttrs: {
    lang: 'pt',
  },
  meta: [
    {
      name: "description",
      content: "Bem-vindo ao The Books Club, a nova plataforma amigável onde você pode falar livremente sobre as coisas de que gosta."
    }
  ],
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/pt"
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
    <h1 class="text-warning fw-bold text-center">Bem-vindo ao The Books Club</h1>
    
    <p class="text-center mt-4 p-outside">Estamos felizes que você finalmente chegou ao nosso site.<br>Nesta página você encontrará uma breve descrição deste projeto e de seus recursos; se tiver interesse, continue lendo.<br>Por outro lado, se você já nos conhece ou já está convencido, pode ir direto para a ação e seguir para <RouterLink to="/registration" style="color:#ffc107; font-weight: bold; text-decoration:none;">Registro</RouterLink> ou <RouterLink to="/login" style="color:#ffc107; font-weight: bold; text-decoration:none;">Login</RouterLink>.</p>
    
    <p class="text-center mt-4 p-outside">Em poucas palavras, esta plataforma é uma rede social onde as pessoas podem falar sobre o que quiserem.<br>Este projeto foi inicialmente pensado para todos os amantes de literatura, dando a eles um lugar onde pudessem discutir sobre seus livros favoritos.<br>Nós realmente acreditamos que esse hobby maravilhoso (o hobby da leitura) pode contribuir para criar pessoas melhores e, de modo geral, um mundo melhor.<br>Mas esta plataforma não é apenas sobre livros.<br>Levamos nossa ideia original adiante e a aplicamos a outras categorias, o que levou à estrutura atual do site.</p>
    
    <p class="text-center mt-4 p-outside">Como você pode ver, há diferentes seções, divididas por tema, para onde você pode direcionar suas postagens.<br>Quando você cria uma postagem pertencente a uma determinada categoria, ela será exibida na seção dessa categoria.<br>Todas as postagens, independentemente da categoria, serão exibidas na página inicial, para que você não perca nada.<br>Ao criar uma postagem, você pode optar por torná-la pessoal; desse modo, ela será exibida apenas na sua página de perfil.<br>Esperamos que essa estrutura ajude nossos usuários a focar no que realmente gostam e desejam de uma rede social, e que facilite um ambiente positivo para as pessoas interagirem umas com as outras.</p>
    
    <p class="text-center mt-4 p-outside">Nossa ideia é oferecer aos usuários um lugar onde possam trocar ideias livremente e sem a preocupação de se exporem publicamente.<br>Achamos que a estrutura atual do projeto é justamente o que pode levar a esse resultado.<br>Um de nossos principais focos é a privacidade do usuário; como você verá ao continuar usando esta plataforma.<br>Você nunca será solicitado a compartilhar qualquer informação pessoal.<br>Pediremos apenas o nome de usuário e o seu endereço de e-mail para o registro.<br>Você pode personalizar seu perfil fornecendo informações sobre você na sua página de perfil, mas apenas se quiser e achar apropriado.</p>
    
    <p class="text-center mt-4 p-outside">Por favor, tenha em mente que, como não pedimos nenhuma permissão de funcionalidade no seu dispositivo, você não poderá receber notificações quando a plataforma estiver fechada.<br>Sabemos que isso pode incomodar alguns usuários, mas, em perspectiva, preferimos dessa forma.<br>Gostaríamos que os usuários viessem à nossa plataforma porque querem se divertir, e não por outros motivos.</p>
    
    <div class="separator separator-class d-flex align-items-center justify-content-center text-danger gap-3">
      <div class="flex-grow-1 border-top border-danger"></div>
        <span class="text-center ">FAQ</span>
      <div class="flex-grow-1 border-top border-danger"></div>
    </div>
    
    <p class="text-center mt-4 p-outside">Aqui você pode encontrar as respostas para as principais dúvidas que um usuário pode ter ao começar a usar nossa plataforma.</p>
    
    <ul>
      <li class="p-outside text-warning" @click="toggleRes1" style="cursor: pointer;">É gratuito usar?</li>
      <p v-show="showRes1" class="mt-2 p-outside">No momento, todas as funcionalidades da plataforma são gratuitas.<br>Está planejada a inclusão de uma pequena assinatura para o serviço de chat privado, com preço de 0,99€ por mês, sem impostos.<br>Os usuários serão notificados quando a assinatura for introduzida.</p>
      
      <li class="p-outside text-warning" @click="toggleRes2" style="cursor: pointer;">Eu preciso de uma conta para explorar o conteúdo?</li>
      <p v-show="showRes2" class="mt-2 p-outside">Você não precisa, estritamente, de uma conta para explorar o conteúdo.<br>No momento, todo o material público pode ser visualizado também por usuários que não estão conectados.<br>Podemos mudar essa política caso percebamos que ela não é saudável para a comunidade.</p>
      
      <li class="p-outside text-warning" @click="toggleRes3" style="cursor: pointer;">Meu perfil é público ou privado?</li>
      <p v-show="showRes3" class="mt-2 p-outside">No momento, as contas de usuário são públicas, pois ainda não implementamos a opção de torná-las privadas.<br>Podemos considerar introduzir a funcionalidade de contas privadas no futuro.<br>Se você quiser ocultar sua conta temporariamente, pode suspender seu usuário na sua página de perfil, no modo de edição.<br>O modo de edição é ativado ao clicar nos “…” ao lado do seu nome de usuário na página de perfil.<br>Quando seu usuário está suspenso, seu conteúdo não ficará disponível para ninguém até a reativação.<br>Se você não quiser mais interagir com um usuário específico, pode bloqueá-lo na página de perfil dele.</p>
      
      <li class="p-outside text-warning" @click="toggleRes4" style="cursor: pointer;">Posso excluir minha conta?</li>
      <p v-show="showRes4" class="mt-2 p-outside">Sim, você pode excluir sua conta, e o processo é muito simples.<br>Você só precisa ir à sua página de perfil, no modo de edição, clicar no botão “Excluir Conta” e seguir o procedimento.<br>Se você quiser mais informações, consulte os <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Termos de Serviço</a> para uma lista mais completa.</p>
      
      <li class="p-outside text-warning" @click="toggleRes5" style="cursor: pointer;">Como a plataforma lida com a privacidade?</li>
      <p v-show="showRes5" class="mt-2 p-outside">A resposta curta é: não compartilhamos informações dos usuários com terceiros e usamos apenas cookies essenciais, estritamente necessários para o funcionamento da aplicação.<br>Se você quiser mais detalhes, dê uma olhada na <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">Política de Privacidade</a></p>
      
      <li class="p-outside text-warning" @click="toggleRes6" style="cursor: pointer;">Empresas ou criadores podem usar a plataforma?</li>
      <p v-show="showRes6" class="mt-2 p-outside">No momento, a plataforma está aberta apenas para usuários comuns.<br>Para empresas, oferecemos um serviço de anúncios totalmente auto-hospedado e que não envolve terceiros.<br>Se você quiser mais informações, visite a página <RouterLink to="/info-contacts" style="color:#ffc107; font-weight: bold; text-decoration:none;">Informações e Contatos</RouterLink> ou entre em contato conosco pelo <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span></p>
      
      <li class="p-outside text-warning" @click="toggleRes7" style="cursor: pointer;">Como funciona a moderação de conteúdo?</li>
      <p v-show="showRes7" class="mt-2 p-outside">Dadas nossas responsabilidades com os usuários, é necessário moderar o conteúdo para manter um ambiente seguro.<br>A moderação de mídia é feita principalmente por meio do uso de um algoritmo de aprendizado de máquina.<br>Quanto ao conteúdo escrito, inspecionamos nossa plataforma constantemente. Para ambos os casos, também contamos com o feedback dos usuários.<br>Se você notar algum conteúdo que não esteja de acordo com a política descrita nos <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">Termos de Serviço</a>, ou quiser denunciar comportamentos perigosos ou inadequados, avise-nos em <span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span> anexando uma captura de tela; responderemos prontamente.</p>
      
      <li class="p-outside text-warning" @click="toggleRes8" style="cursor: pointer;">Posso postar em diferentes idiomas?</li>
      <p v-show="showRes8" class="mt-2 p-outside">Sim, você pode postar em vários idiomas.<br>Para mudar o idioma do aplicativo, basta clicar no botão do globo que você encontra em qualquer página e escolher o idioma desejado.<br>Observe que, quando você posta em um idioma, sua postagem será visível apenas nesse idioma; ela não será traduzida automaticamente para outros.<br>Portanto, se você quiser que uma postagem apareça em dois idiomas diferentes, precisará criá-la nos dois idiomas de forma independente.</p>
      
      <li class="p-outside text-warning" @click="toggleRes9" style="cursor: pointer;">Como funcionam as notificações?</li>
      <p v-show="showRes9" class="mt-2 p-outside">Como já mencionado, como não pedimos permissões no seu dispositivo, você não receberá notificações quando a plataforma estiver fechada.<br>No entanto, assim que você fizer login novamente, as notificações sobre comentários, menções ou mensagens recebidas serão exibidas nos dois botões na barra superior.<br>Se você clicar em uma notificação exibida (por exemplo, uma resposta a um comentário), a plataforma levará você diretamente ao objeto da notificação.</p>
      
    </ul>
    
    <p class="text-center mt-4 p-outside mb-5">Você ainda tem dúvidas ou quer entrar em contato conosco por outro motivo?<br>Você pode entrar em contato pelo <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>. Ficaremos felizes em ajudar.</p>
      
  </div>
</template>
