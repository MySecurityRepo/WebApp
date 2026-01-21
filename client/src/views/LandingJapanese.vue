<script setup>
import { useHead } from '@vueuse/head'
import { RouterLink } from 'vue-router'
import { ref } from 'vue';


useHead({
  title: "The Books Club - みんなのためのブログ",
  htmlAttrs: {
    lang: 'ja',
  },
  meta: [
    {
      name: "description",
      content: "The Books Club へようこそ。ここは、あなたが好きなことを自由に話せる、新しいユーザーフレンドリーなプラットフォームです。"
    }
  ],
  link: [
    {
      rel: "canonical",
      href: "https://thebooksclub.com/ja"
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
    <h1 class="text-warning fw-bold text-center">The Books Club へようこそ。</h1>
    
    <p class="text-center mt-4 p-outside">あなたがついに私たちのサイトに来てくれて、とても嬉しいです。<br>このページでは、このプロジェクトとその機能についての簡単な説明をご覧いただけます。興味があれば、そのまま読み進めてください。<br>一方ですでに私たちを知っている場合や、すでに納得している場合は、すぐに行動に移して <RouterLink to="/registration" style="color:#ffc107; font-weight: bold; text-decoration:none;">登録</RouterLink>または<RouterLink to="/login" style="color:#ffc107; font-weight: bold; text-decoration:none;">ログイン</RouterLink>.</p>
    
    <p class="text-center mt-4 p-outside">ひと言で言えば、このプラットフォームは、人々が好きなことについて自由に話せるソーシャルネットワークです。<br>このプロジェクトは当初、文学を愛する人たちが、自分の好きな本について語り合える場を提供することを目的に考えられたものでした。<br>私たちは、この素晴らしい趣味（読書という趣味）が、より良い人々を、そして全体としてより良い世界をつくることに貢献できると本気で考えています。<br>しかし、このプラットフォームは本のことだけではありません。<br>私たちは当初のアイデアをさらに発展させ、他のカテゴリにも適用しました。その結果、現在のサイト構造が生まれました。</p>
    
    <p class="text-center mt-4 p-outside">ご覧のとおり、トピックごとに分けられたさまざまなセクションがあり、あなたの投稿を振り分けることができます。<br>投稿を特定のカテゴリに属するものとして作成すると、そのカテゴリのセクションに表示されます。<br>すべての投稿は、カテゴリに関係なくホームページに表示されるため、見逃すことはありません。<br>投稿を作成する際、パーソナルに設定することもできます。その場合、その投稿はあなたのプロフィールページにのみ表示されます。<br>この構造が、ユーザーが本当に好きなことやソーシャルネットワークに求めるものに集中できるようになり、人々が互いに交流するための前向きな環境づくりに役立つことを願っています。</p>
    
    <p class="text-center mt-4 p-outside">私たちの考えは、ユーザーが自由にアイデアを交換でき、公共の場で自分をさらす心配をせずに済む場所を提供することです。<br>現在のプロジェクト構造こそが、その結果につながると私たちは考えています。<br>はユーザーのプライバシーです。このプラットフォームを使い進めていけば、それが分かるはずです。<br>あなたに個人情報の提供を求めることは決してありません。<br>登録の際に求めるのは、ユーザー名とメールアドレスだけです。<br>プロフィールページで自分に関する情報を入力してプロフィールをカスタマイズできますが、それはあなたが望み、適切だと思う場合に限られます。</p>
    
    <p class="text-center mt-4 p-outside">お使いのデバイスで機能的な権限を一切求めていないため、プラットフォームを閉じている間は通知を受け取れないことに注意してください。<br>これは一部のユーザーにとって不便かもしれませんが、将来的な視点から私たちはこの方法を選んでいます。<br>ユーザーには、別の理由ではなく、楽しい時間を過ごしたいからこそこのプラットフォームに来てほしいと考えています。</p>
    
    <div class="separator separator-class d-flex align-items-center justify-content-center text-danger gap-3">
      <div class="flex-grow-1 border-top border-danger"></div>
        <span class="text-center ">FAQ</span>
      <div class="flex-grow-1 border-top border-danger"></div>
    </div>
    
    <p class="text-center mt-4 p-outside">ここでは、ユーザーがこのプラットフォームを使い始める際に抱く主な疑問への答えを見つけることができます。</p>
    
    <ul>
      <li class="p-outside text-warning" @click="toggleRes1" style="cursor: pointer;">利用は無料ですか？</li>
      <p v-show="showRes1" class="mt-2 p-outside">現時点では、プラットフォームのすべての機能は無料です。<br>プライベートチャットサービスには小さなサブスクリプションを導入する予定で、価格は月額0.99€（税抜）になります。<br>サブスクリプション導入時にはユーザーに通知されます。</p>
      
      <li class="p-outside text-warning" @click="toggleRes2" style="cursor: pointer;">コンテンツを閲覧するのにアカウントは必要ですか？</li>
      <p v-show="showRes2" class="mt-2 p-outside">コンテンツを閲覧するために必ずしもアカウントは必要ありません。<br>現時点では、すべての公開されている内容は、サインインしていないユーザーでも閲覧できます。<br>ただし、この方針がコミュニティにとって健全でないと判断した場合、変更する可能性があります。</p>
      
      <li class="p-outside text-warning" @click="toggleRes3" style="cursor: pointer;">私のプロフィールは公開ですか、それとも非公開ですか？</li>
      <p v-show="showRes3" class="mt-2 p-outside">現時点では、アカウントの非公開設定を実装していないため、ユーザーアカウントは公開となっています。<br>将来的に、アカウントを非公開にする機能を導入することを検討する可能性があります。<br>一時的にアカウントを非表示にしたい場合は、プロフィールページの編集モードでユーザーを一時停止できます。<br>編集モードは、プロフィールページでユーザー名の横にある「…」をクリックすることで有効になります。<br>ユーザーを一時停止している間は、再有効化するまであなたのコンテンツは誰にも表示されません。<br>特定のユーザーとこれ以上関わりたくない場合は、そのユーザーのプロフィールページでブロックできます。</p>
      
      <li class="p-outside text-warning" @click="toggleRes4" style="cursor: pointer;">アカウントを削除できますか？</li>
      <p v-show="showRes4" class="mt-2 p-outside">はい、アカウントを削除できますし、その手順はとても簡単です。<br>プロフィールページの編集モードに入り、「アカウント削除」ボタンをクリックして手順に従うだけです。<br>さらに詳しい情報が必要な場合は、より包括的なチェックリストとして<a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">利用規約</a> をご覧ください。</p>
      
      <li class="p-outside text-warning" @click="toggleRes5" style="cursor: pointer;">このプラットフォームはプライバシーをどのように扱っていますか？</li>
      <p v-show="showRes5" class="mt-2 p-outside">短い答えとしてはこうです：私たちはユーザー情報を第三者と共有せず、アプリケーションの機能に厳密に必要な最低限のクッキーのみを使用しています。<br>より詳しい情報が必要な場合は、 <a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/PrivacyPolicy.html">プライバシーポリシー</a> をご覧ください。</p>
      
      <li class="p-outside text-warning" @click="toggleRes6" style="cursor: pointer;">企業やクリエイターはこのプラットフォームを利用できますか？</li>
      <p v-show="showRes6" class="mt-2 p-outside">現時点では、プラットフォームは一般ユーザーのみが利用できます。<br>企業向けには、完全に自社運用で、第三者を介さない広告サービスを提供しています。<br>さらに詳しい情報が必要な場合は、 <RouterLink to="/info-contacts" style="color:#ffc107; font-weight: bold; text-decoration:none;">情報とお問い合わせ</RouterLink> ページをご覧いただくか、 <span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span> までご連絡ください。</p>
      
      <li class="p-outside text-warning" @click="toggleRes7" style="cursor: pointer;">コンテンツのモデレーションはどのように行われていますか？</li>
      <p v-show="showRes7" class="mt-2 p-outside">ユーザーに対する私たちの責任を踏まえると、安全な環境を維持するためにコンテンツをモデレーションすることが必要です。<br>メディアのモデレーションは、主に機械学習アルゴリズムを用いて行われています。<br>書かれたコンテンツに関しては、私たちは常にプラットフォームを監視しています。どちらの場合も、ユーザーからのフィードバックにも依存しています。<br><a style="color:#ffc107; font-weight: bold; text-decoration:none;" href="https://thebooksclub.com/docs/TermsofService.html">利用規約</a>, に記載されているポリシーに沿っていないコンテンツに気付いた場合、または危険な・不適切な行為を報告したい場合は、スクリーンショットを添付して <span style="color:#ffc107; font-weight: bold;">abuse@thebooksclub.com</span> までご連絡ください。速やかに対応いたします。</p>
      
      <li class="p-outside text-warning" @click="toggleRes8" style="cursor: pointer;">異なる言語で投稿できますか？</li>
      <p v-show="showRes8" class="mt-2 p-outside">はい、複数の言語で投稿できます。<br>アプリケーションの言語を変更するには、どのページにもある地球儀ボタンをクリックし、希望の言語を選択してください。<br>投稿を特定の言語で行った場合、その投稿はその言語でのみ表示され、他の言語に自動翻訳されることはありません。<br>したがって、例えば 2 つの異なる言語で投稿を表示させたい場合は、それぞれの言語で独立して投稿を作成する必要があります。</p>
      
      <li class="p-outside text-warning" @click="toggleRes9" style="cursor: pointer;">通知はどのように機能しますか？</li>
      <p v-show="showRes9" class="mt-2 p-outside">すでに述べたように、私たちはお使いのデバイスに権限を要求していないため、プラットフォームを閉じている間は通知を受け取ることはできません。<br>しかし、再度サインインすると、受け取ったコメント、メンション、メッセージに関する通知がトップバーの2つのボタンに表示されます。<br>表示された通知（例：コメントへの返信）をクリックすると、その通知の対象へ直接移動します。</p>
      
    </ul>
    
    <p class="text-center mt-4 p-outside mb-5">まだ質問がある場合や、ほかの理由で私たちに連絡したい場合はありますか？<br><span style="color:#ffc107; font-weight: bold;">contacts@thebooksclub.com</span>でご連絡いただけます。喜んでお手伝いさせていただきます。</p>
      
  </div>
</template>
