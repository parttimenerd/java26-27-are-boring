---
theme: default
colorSchema: dark
class: text-center
highlighter: shiki
lineNumbers: false
info: |
  Java 26 and 27 are boring and this is a good thing.
  A talk by Lutske van der Meer and Johannes Bechberger
drawings:
  persist: false
transition: slide-left
title: Java 26 and 27 are boring and this is a good thing
mdc: true
---

<script setup>
import { onMounted, onUnmounted } from 'vue'

const boringFeatureEnabled = import.meta.env.VITE_BORING_ENABLED === 'true'
const base = import.meta.env.BASE_URL.replace(/\/$/, '')
const boringSoundManifestUrl = `${base}/sounds/manifest.json`
const fallbackBoringSounds = [
  `${base}/sounds/quebec.opus`,
  `${base}/sounds/quebec1.opus`,
  `${base}/sounds/boring-1.wav`,
  `${base}/sounds/boring-2.wav`,
  `${base}/sounds/boring-3.wav`
]
const boringManifestRefreshMs = 15000
let currentBoringSounds = [...fallbackBoringSounds]
let manifestRefreshTimer = null
let boringPlaybackQueue = []
const activeBoringAudios = new Set()
let boringAudioContext = null
let boringCompressorNode = null
let boringOutputGainNode = null
const boringLogPrefix = '[boring-sound]'

function boringLog(level, message, details) {
  if (details === undefined) {
    console[level](`${boringLogPrefix} ${message}`)
    return
  }
  console[level](`${boringLogPrefix} ${message}`, details)
}

function shuffleArray(items) {
  const result = [...items]
  for (let index = result.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1))
    const currentValue = result[index]
    result[index] = result[randomIndex]
    result[randomIndex] = currentValue
  }
  return result
}

async function ensureBoringAudioChain() {
  if (!window.AudioContext && !window.webkitAudioContext) {
    return null
  }

  if (!boringAudioContext) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    boringAudioContext = new AudioContextClass()

    boringCompressorNode = boringAudioContext.createDynamicsCompressor()
    boringCompressorNode.threshold.value = -24
    boringCompressorNode.knee.value = 20
    boringCompressorNode.ratio.value = 8
    boringCompressorNode.attack.value = 0.01
    boringCompressorNode.release.value = 0.25

    boringOutputGainNode = boringAudioContext.createGain()
    boringOutputGainNode.gain.value = 0.95

    boringCompressorNode.connect(boringOutputGainNode)
    boringOutputGainNode.connect(boringAudioContext.destination)

    boringLog('info', 'Initialized boring audio normalization chain')
  }

  if (boringAudioContext.state === 'suspended') {
    await boringAudioContext.resume()
    boringLog('debug', 'Resumed boring audio context')
  }

  return boringAudioContext
}

async function connectAudioToNormalizationChain(audio, url) {
  const context = await ensureBoringAudioChain()
  if (!context || !boringCompressorNode) {
    boringLog('debug', 'Web Audio normalization unavailable, using element volume only', { url })
    return null
  }

  const sourceNode = context.createMediaElementSource(audio)
  sourceNode.connect(boringCompressorNode)
  return sourceNode
}

async function refreshBoringSounds() {
  boringLog('debug', 'Refreshing boring sound manifest', {
    url: boringSoundManifestUrl,
    intervalMs: boringManifestRefreshMs
  })

  return fetch(boringSoundManifestUrl, { cache: 'no-store' })
    .then((response) => {
      if (!response.ok) {
        throw new Error('Failed to load boring sound manifest')
      }
      return response.json()
    })
    .then((manifest) => {
      const files = Array.isArray(manifest?.files) ? manifest.files : []
      const resolved = files
        .filter((file) => typeof file === 'string' && file.trim().length > 0)
        .map((file) => (file.startsWith('/') ? file : `${base}/sounds/${file}`))

      currentBoringSounds = resolved.length > 0 ? [...new Set(resolved)] : [...fallbackBoringSounds]
      boringPlaybackQueue = []
      boringLog('info', 'Resolved boring sound list', {
        fromManifest: resolved.length > 0,
        count: currentBoringSounds.length,
        files: currentBoringSounds
      })
      return currentBoringSounds
    })
    .catch((error) => {
      currentBoringSounds = currentBoringSounds.length > 0 ? currentBoringSounds : [...fallbackBoringSounds]
      boringLog('warn', 'Manifest load failed, using fallback boring sounds', {
        error: String(error),
        count: currentBoringSounds.length,
        files: currentBoringSounds
      })
      return currentBoringSounds
    })
}

function startBoringManifestRefresh() {
  refreshBoringSounds()

  if (manifestRefreshTimer) {
    window.clearInterval(manifestRefreshTimer)
  }

  manifestRefreshTimer = window.setInterval(() => {
    refreshBoringSounds()
  }, boringManifestRefreshMs)
}

function stopBoringManifestRefresh() {
  if (!manifestRefreshTimer) return
  window.clearInterval(manifestRefreshTimer)
  manifestRefreshTimer = null
}

function getCurrentSlideElement(event) {
  const target = event?.target

  if (target instanceof HTMLElement) {
    const closestSlide = target.closest('.slidev-page, .slidev-layout')
    if (closestSlide) {
      return closestSlide
    }
  }

  return document.querySelector('.slidev-page.slidev-page-current, .slidev-page, .slidev-layout')
}

function isNonBoringSlide(event) {
  const slideElement = getCurrentSlideElement(event)
  if (!slideElement) return false

  return (
    slideElement.classList.contains('non-boring') ||
    slideElement.classList.contains('no-boring') ||
    slideElement.dataset.nonBoring === 'true' ||
    slideElement.getAttribute('data-boring') === 'false'
  )
}

function isIgnoredBoringContext(event) {
  if (window.__terminalIsOpen === true) {
    return true
  }

  const activeElement = document.activeElement
  const target = event?.target

  if (activeElement?.tagName === 'IFRAME') {
    return true
  }

  const ignoreSelector = '.modal-overlay, .modal-container, .code-runner, .cm-editor, .terminal-container, [role="dialog"]'
  const inputSelector = 'input, textarea, select, [contenteditable="true"]'

  if (target instanceof HTMLElement) {
    if (target.closest(ignoreSelector) || target.closest(inputSelector)) {
      return true
    }
  }

  if (activeElement instanceof HTMLElement) {
    if (activeElement.closest(ignoreSelector) || activeElement.closest(inputSelector)) {
      return true
    }
  }

  return false
}

async function playRandomBoringSound() {
  const boringSounds = currentBoringSounds
  if (boringSounds.length === 0) {
    boringLog('warn', 'No boring sounds available to play')
    return
  }

  if (boringPlaybackQueue.length === 0) {
    boringPlaybackQueue = shuffleArray(boringSounds)
    boringLog('debug', 'Started new randomized boring sound cycle', {
      cycleLength: boringPlaybackQueue.length,
      queue: boringPlaybackQueue
    })
  }

  const selectedSound = boringPlaybackQueue.shift()
  const shuffledSounds = [selectedSound, ...boringPlaybackQueue]

  boringLog('debug', 'Selected next boring sound from randomized cycle', {
    selected: shuffledSounds[0],
    remainingInCycle: boringPlaybackQueue.length,
    totalCandidatesThisAttempt: shuffledSounds.length
  })

  const tryPlayAtIndex = (index) => {
    if (index >= shuffledSounds.length) {
      boringLog('warn', 'Exhausted boring sounds without successful playback')
      return
    }

    const url = shuffledSounds[index]
    boringLog('debug', 'Attempting to play boring sound', { index, url })

    const audio = new Audio(url)
    audio.volume = 1
    let mediaSourceNode = null

    connectAudioToNormalizationChain(audio, url)
      .then((sourceNode) => {
        mediaSourceNode = sourceNode
        return audio.play()
      })
      .then(() => {
        activeBoringAudios.add(audio)
        if (index > 0) {
          boringPlaybackQueue = boringPlaybackQueue.filter((queuedUrl) => queuedUrl !== url)
        }
        boringLog('info', 'Playing boring sound', { url })

        audio.addEventListener('ended', () => {
          activeBoringAudios.delete(audio)
          if (mediaSourceNode) {
            try {
              mediaSourceNode.disconnect()
            } catch {}
            mediaSourceNode = null
          }
          try {
            audio.pause()
            audio.src = ''
          } catch {}
          boringLog('debug', 'Boring sound ended', { url })
        }, { once: true })

        audio.addEventListener('error', () => {
          activeBoringAudios.delete(audio)
          if (mediaSourceNode) {
            try {
              mediaSourceNode.disconnect()
            } catch {}
            mediaSourceNode = null
          }
          boringLog('warn', 'Boring sound emitted error while playing', { url })
        }, { once: true })
      })
      .catch((error) => {
        boringLog('warn', 'Failed to play boring sound candidate', {
          url,
          error: String(error)
        })
        if (currentBoringSounds) {
          currentBoringSounds = currentBoringSounds.filter((cachedUrl) => cachedUrl !== url)
          boringPlaybackQueue = boringPlaybackQueue.filter((queuedUrl) => queuedUrl !== url)
          boringLog('debug', 'Removed failing boring sound from cache', {
            removed: url,
            remaining: currentBoringSounds.length
          })
        }
        tryPlayAtIndex(index + 1)
      })
  }

  tryPlayAtIndex(0)
}

function handleBoringEnter(event) {
  if (!boringFeatureEnabled) return

  if (event.key !== 'Enter') return

  if (event.defaultPrevented) {
    boringLog('debug', 'Ignoring Enter: default already prevented')
    return
  }
  if (event.repeat) {
    boringLog('debug', 'Ignoring Enter: key repeat')
    return
  }
  if (event.ctrlKey || event.metaKey || event.altKey) {
    boringLog('debug', 'Ignoring Enter: modifier key pressed', {
      ctrl: event.ctrlKey,
      meta: event.metaKey,
      alt: event.altKey
    })
    return
  }
  if (isIgnoredBoringContext(event)) {
    boringLog('debug', 'Ignoring Enter: ignored focus context')
    return
  }
  if (isNonBoringSlide(event)) {
    boringLog('debug', 'Ignoring Enter: slide marked non-boring')
    return
  }

  boringLog('debug', 'Enter accepted: triggering boring sound playback')

  playRandomBoringSound()
}

onMounted(() => {
  // Set code editor font sizes globally
  // Change these values to customize code display across all slides
  const rootElement = document.documentElement
  rootElement.style.setProperty('--code-font-size-px', '14px')

  boringLog('info', 'Boring sound feature initialized', {
    enabled: boringFeatureEnabled,
    manifestUrl: boringSoundManifestUrl,
    manifestRefreshMs: boringManifestRefreshMs
  })

  startBoringManifestRefresh()

  window.addEventListener('keydown', handleBoringEnter)
})

onUnmounted(() => {
  stopBoringManifestRefresh()
  window.removeEventListener('keydown', handleBoringEnter)
})
</script>




<div class="relative z-10 flex flex-col items-center justify-center h-full">

<div class="text-6xl font-bold leading-tight">Java 26 and 27 are boring</div>
<div class="text-3xl mt-4 text-emerald-400 font-semibold">and this is a good thing</div>

<div class="mt-12 text-xl text-gray-500">
Lutske van der Meer &nbsp;&nbsp;·&nbsp;&nbsp; Johannes Bechberger
</div>

<div class="mt-4 text-lg text-gray-400">J-Fall 2026</div>

</div>

<!--
L: Welcome
-->

---
layout: center
---


<div class="relative z-10">

# Boring.

<v-click>

<div class="text-2xl text-gray-300 mt-8">

Predictable. No surprises. Works at 3 AM.

</div>

<div class="text-xl text-gray-400 mt-4">

Your code still compiles. Your APIs still work.<br/>Your upgrade is not a rewrite.

</div>

</v-click>

</div>

<!--
L: "When people hear 'boring tech,' they think old, slow, or not innovative."
-->

---

# Who are we?

<div class="grid grid-cols-2 gap-12 mt-12">

<div class="text-center">

### Lutske

<div class="text-gray-400 mt-4 text-lg">

Java Developer @ Craftsmen<br/>
JUG lead of:<br/>
JUG Noord & Apeldoorn JUG<br/>
Organizer of Devoxx4kids

</div>
</div>

<div class="text-center">

### Johannes

<div class="text-gray-400 mt-4 text-lg">

OpenJDK Developer @ SAP<br/>
Java Champion<br/>
Blogger<br/>
<br/>

</div>
</div>

<v-click>

# Boring.
</v-click>

</div>

<!--
L: ""
J:
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement text-5xl">

What Java version are you on?

</div>

<div class="text-xl text-gray-400 mt-8">


</div>

</div>

<!--
L: "Quick show of hands. Who' on Java 28? Liars, it's not out there Who's on 26, 25, 24, 17 11, 8, 5, below 5?"
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

Many platforms try to impress you with <OrangeText>✨shiny rewrites✨</OrangeText>and <RedText> breaking changes 🚨</RedText>

</div>

<v-click>

<div class="text-3xl mt-8 font-semibold text-center">

Java took another path. Java optimizes for <OrangeText>trust</OrangeText>.

</div>

</v-click>

</div>

<!--
L: "Most platforms chase shiny new syntax. Java optimizes for something rarer: trust."
[click]
"Trust that your code still compiles. Trust that an upgrade won't turn into a migration project. Trust that what you shipped three years ago still runs. That's thirty years of evidence, not marketing. So when someone calls Java boring, they're paying its biggest compliment."
-->

---
layout: center
---


<div class="relative z-10">

<div class="big-statement">

Boring by design, since 1995

</div>

<div class="mt-8 text-xl leading-loose">

✅ Simple, object-oriented, and <OrangeText>**familiar**</OrangeText>

✅ **Robust** and **secure**

✅ Architecture-neutral and **portable**

✅ High **performance**

✅ Interpreted, threaded, and dynamic

</div>

<div class="text-sm text-gray-500 mt-6"> The five original design goals, Java Language Specification, 1995</div>

</div>

<!--
all Johannes:

If you didn't know it, Java had five original design goals, set out in 1995:

...

"Boring wasn't an accident.
"Simple, object-oriented, and familiar. Not 'revolutionary.' Not 'paradigm-shifting.' Familiar."
"High performance — though early Java was actually quite slow. JIT compilation in 1997 changed everything."
"Java was designed to be boring. And the trust we just talked about? It was baked in from day one."
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

How to upgrade to Java 27

</div>

<div class="mt-12">

```xml
<!-- Maven: just change this -->
<maven.compiler.release>27</maven.compiler.release>
```

</div>

<div class="mt-4">

```groovy
// Gradle: just change this
java { toolchain { languageVersion = JavaLanguageVersion.of(27) } }
```

</div>


<div class="text-xl text-gray-400 mt-8">

That's it. Seriously.
</div>

</div>

<!--
Johannes
-->

---
layout: center
---


<div class="relative z-10">

<div class="big-statement">

You can write Java 8 code<br/>and <RedText>nobody</RedText> will notice.

</div>

<v-click>

<div class="text-xl mt-8">

The only new syntax:
- `var`
- `switch`/`instanceof`
- `record`
- text blocks

</div>

</v-click>

</div>

<!--
all Johannes:

"Here's something people don't realize: the Java language itself hasn't changed that dramatically since Java 8."
[click]
Syntax sugar

"Var is syntax sugar. Records are syntax sugar. Even switch expressions and pattern matching are just evolutions of existing syntax. And hey, we did some research: most of your code doesn't use these new features anyway."

One could argue most Java releases after Java 8 are boring
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

The ecosystem is the <OrangeText>real</OrangeText> innovator.

</div>

</div>

<!--
Lutske:
Java 26 is boring → ecosystem shines
- Many conferences → ideas spread fast
- JUGs (10 here!) → real discussions, real feedback
- JUG Square → where ideas get challenged & refined

Libraries = where innovation happens
- Open source moves faster than the JDK
- Experiments → libraries → real-world usage
- Proven ideas → eventually become JEPs

Key message
- Innovation starts in the community
- Java stays stable on purpose
- Ecosystem = the real innovator 🚀
-->

---
layout: center
---

<div class="big-statement">

Your code was already <span class="text-emerald">boring</span>.

</div>

<!--
Lutske: We did some research… and found that a lot of code still doesn’t use modern features.

So what did we learn?

Complex generics? 2004.
Try-with-resources? 2011.
Records… still feel futuristic, but they’re already 5 years old.

Half of what we call “modern Java” predates your smartphone.

The code you write every day?
It’s built on features that are a decade or even two decades old.
And it still works.

Your code was already boring.
And it still compiles on Java 26.

That’s not a complaint.
That’s an achievement.
-->


---
layout: section
---

<div class="absolute inset-0 flex flex-col items-center justify-between" style="background-image: url('./img/Duke_releasetrain.png'); background-size: cover; background-position: center;">
  <div class="flex-1"></div>
  <div class="text-center pb-12">
    <h1 class="text-white drop-shadow-lg inline-block px-4 py-2 rounded" style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(8px);">The Release Train</h1>
  </div>
  <div class="absolute bottom-4 right-4 text-sm text-re text-black " style="background: rgba(255, 255, 255, 0.15); backdrop-filter: blur(8px);">
    Based on <a href="https://www.youtube.com/watch?v=K40XrR67fas" class="text-black">https://www.youtube.com/watch?v=K40XrR67fas
</a>
  </div>
</div>

<!--
all Johannes:

"In the early 1990s, Java was initially developed by James Gosling and his team at Sun Microsystems for a project called “Green Project.” The goal was to create a platform-independent language for consumer electronic devices like interactive TVs, VCRs, and set-top boxes.

However, they realized that the television market wasn’t quite ready for such advanced software. The team then shifted their focus to the burgeoning internet era, where Java found its true calling as a language for web applications. Its “write once, run anywhere” capability became one of its defining features, revolutionizing web development.

"Designed for TV, named after coffee, ended up running 95% of the Fortune 500. Let's look at the before and after."
-->

---

# Before 2017: Chaos

<svg viewBox="-30 0 1060 420" class="w-full" style="font-size: 1px;">
  <!-- Timeline: Java 5 (2004) → Java 9 (2017). 13 years. -->
  <!-- X positions proportional: J5→60  J6→190  J7→512  J8→706  J9→900 -->

  <!-- Main horizontal timeline line -->
  <line x1="30" y1="210" x2="930" y2="210" stroke="#555" stroke-width="2" />

  <!-- === Java 5 (2004) — BOTTOM === -->
  <g>
    <circle cx="60" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="60" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="60" cy="210" r="4" fill="#00bcd4" />
    <line x1="60" y1="224" x2="60" y2="290" stroke="#00bcd4" stroke-width="1.2" />
    <circle cx="60" cy="290" r="2.5" fill="#00bcd4" />
    <text x="60" y="185" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#00bcd4">Java 5</text>
    <text x="60" y="315" text-anchor="middle" style="font-size: 18px;" fill="white">2004 ☕</text>
    <line x1="-10" y1="335" x2="130" y2="335" stroke="#00bcd4" stroke-width="2" />
  </g>

  <!-- === Java 6 (2006) — TOP — 2 year gap === -->
  <g v-click>
    <line x1="74" y1="210" x2="176" y2="210" stroke="#4caf50" stroke-width="5" opacity="0.5" />
    <circle cx="190" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="190" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="190" cy="210" r="4" fill="#4caf50" />
    <line x1="190" y1="196" x2="190" y2="130" stroke="#4caf50" stroke-width="1.2" />
    <circle cx="190" cy="130" r="2.5" fill="#4caf50" />
    <text x="190" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#4caf50">Java 6</text>
    <text x="190" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">2006 — 2 years ⏱️</text>
    <line x1="90" y1="96" x2="290" y2="96" stroke="#4caf50" stroke-width="2" />
  </g>

  <!-- === Java 7 (2011) — BOTTOM — 5 year gap === -->
  <g v-click>
    <line x1="204" y1="210" x2="498" y2="210" stroke="#e91e63" stroke-width="5" opacity="0.5" />
    <circle cx="512" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="512" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="512" cy="210" r="4" fill="#e91e63" />
    <line x1="512" y1="224" x2="512" y2="290" stroke="#e91e63" stroke-width="1.2" />
    <circle cx="512" cy="290" r="2.5" fill="#e91e63" />
    <text x="512" y="185" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#e91e63">Java 7</text>
    <text x="512" y="315" text-anchor="middle" style="font-size: 18px;" fill="white">2011 — 5 years 💀</text>
    <line x1="412" y1="335" x2="612" y2="335" stroke="#e91e63" stroke-width="2" />
  </g>

  <!-- === Java 8 (2014) — TOP — 3 year gap === -->
  <g v-click>
    <line x1="526" y1="210" x2="692" y2="210" stroke="#ff9800" stroke-width="5" opacity="0.5" />
    <circle cx="706" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="706" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="706" cy="210" r="4" fill="#ff9800" />
    <line x1="706" y1="196" x2="706" y2="130" stroke="#ff9800" stroke-width="1.2" />
    <circle cx="706" cy="130" r="2.5" fill="#ff9800" />
    <text x="706" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#ff9800">Java 8</text>
    <text x="706" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">2014 — 3 years ⏱️</text>
    <line x1="606" y1="96" x2="806" y2="96" stroke="#ff9800" stroke-width="2" />
  </g>

  <!-- === Java 9 (2017) — BOTTOM — 3.5 year gap === -->
  <g v-click>
    <line x1="720" y1="210" x2="886" y2="210" stroke="#607d8b" stroke-width="5" opacity="0.5" />
    <circle cx="900" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="900" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="900" cy="210" r="4" fill="#607d8b" />
    <line x1="900" y1="224" x2="900" y2="290" stroke="#607d8b" stroke-width="1.2" />
    <circle cx="900" cy="290" r="2.5" fill="#607d8b" />
    <text x="900" y="185" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#607d8b">Java 9</text>
    <text x="900" y="315" text-anchor="middle" style="font-size: 18px;" fill="white">2017 — 3.5 years 😤</text>
    <line x1="800" y1="335" x2="1000" y2="335" stroke="#607d8b" stroke-width="2" />
  </g>
</svg>

<!--
Johannes:


J: "The old release model was a mess."

Java 5 came in in 2024 with generics, annotations, enums and more

Java 6 mostly performance updates

Java 7 with nio, string in switches

Java 8 lambdas and streams

J: "Java 5 to 6: two years. Reasonable. 6 to 7: five years. Five! That's an eternity in tech."
J: "7 to 8: three years. The lambdas release. And 8 to 9: three and a half years. Java 9 was 18 months late because they tried to finish Project Jigsaw — the module system."
L: "And modules were... controversial."
-->

---
layout: center
---


<div class="relative z-10">

<div class="quote-slide">
  <div class="quote-text">
    "Modules: Enormous upheaval<br/> for minimal concrete benefit."
  </div>
  <div class="quote-attr">— Neil Madden, rating 26 years of Java changes</div>
</div>

</div>

<!--
Johannes:

delayed Java 9 by 18 months and broke a lot of build tooling. That's what happens when you try to ship something too big. And that experience led directly to the new model."
-->

---

# After 2017: Cadence

<svg viewBox="-30 0 1060 420" class="w-full" style="font-size: 1px;">
  <!-- Timeline: Java 9 (2017) → Java 17 (2021) -->
  <!-- Equal spacing to show the new 6-month cadence -->
  <!-- X positions: J9→60 J10→170 J11→280 J12→390 J13→500 J14→610 J15→720 J16→830 J17→940 -->

  <!-- Main horizontal timeline line -->
  <line x1="30" y1="210" x2="970" y2="210" stroke="#555" stroke-width="2" />

  <!-- === Java 9 (2017) — TOP === -->
  <g>
    <circle cx="60" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="60" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="60" cy="210" r="4" fill="#607d8b" />
    <line x1="60" y1="196" x2="60" y2="130" stroke="#607d8b" stroke-width="1.2" />
    <circle cx="60" cy="130" r="2.5" fill="#607d8b" />
    <text x="60" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#607d8b">Java 9</text>
    <text x="60" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2017</text>
    <line x1="-10" y1="96" x2="130" y2="96" stroke="#607d8b" stroke-width="2" />
  </g>

  <!-- === Java 10 (2018) — TOP — 6 months === -->
  <g v-click>
    <line x1="74" y1="210" x2="156" y2="210" stroke="#00bcd4" stroke-width="5" opacity="0.5" />
    <circle cx="170" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="170" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="170" cy="210" r="4" fill="#00bcd4" />
    <line x1="170" y1="196" x2="170" y2="130" stroke="#00bcd4" stroke-width="1.2" />
    <circle cx="170" cy="130" r="2.5" fill="#00bcd4" />
    <text x="170" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#00bcd4">Java 10</text>
    <text x="170" y="120" text-anchor="middle" style="font-size: 18px;" fill="white"> Sep 2017</text>
    <line x1="100" y1="96" x2="240" y2="96" stroke="#00bcd4" stroke-width="2" />
  </g>

  <!-- === Java 11 (2018) — BOTTOM — LTS === -->
  <g v-click>
    <line x1="184" y1="210" x2="266" y2="210" stroke="#4caf50" stroke-width="5" opacity="0.5" />
    <circle cx="280" cy="210" r="18" fill="none" stroke="#4caf50" stroke-width="2" />
    <circle cx="280" cy="210" r="11" fill="none" stroke="#4caf50" stroke-width="1.1" />
    <circle cx="280" cy="210" r="5" fill="#4caf50" />
    <line x1="280" y1="228" x2="280" y2="294" stroke="#4caf50" stroke-width="1.2" />
    <circle cx="280" cy="294" r="2.5" fill="#4caf50" />
    <text x="280" y="185" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#4caf50">Java 11</text>
    <text x="280" y="319" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2018 ⭐LTS </text>
    <line x1="200" y1="339" x2="360" y2="339" stroke="#4caf50" stroke-width="2" />
  </g>

  <!-- === Java 12 (2019) — TOP === -->
  <g v-click>
    <line x1="294" y1="210" x2="376" y2="210" stroke="#ff9800" stroke-width="5" opacity="0.5" />
    <circle cx="390" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="390" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="390" cy="210" r="4" fill="#ff9800" />
    <line x1="390" y1="196" x2="390" y2="130" stroke="#ff9800" stroke-width="1.2" />
    <circle cx="390" cy="130" r="2.5" fill="#ff9800" />
    <text x="390" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#ff9800">Java 12</text>
    <text x="390" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2019</text>
    <line x1="320" y1="96" x2="460" y2="96" stroke="#ff9800" stroke-width="2" />
  </g>

  <!-- === Java 13 (2019) — TOP === -->
  <g v-click>
    <line x1="404" y1="210" x2="486" y2="210" stroke="#9c27b0" stroke-width="5" opacity="0.5" />
    <circle cx="500" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="500" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="500" cy="210" r="4" fill="#9c27b0" />
    <line x1="500" y1="196" x2="500" y2="130" stroke="#9c27b0" stroke-width="1.2" />
    <circle cx="500" cy="130" r="2.5" fill="#9c27b0" />
    <text x="500" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#9c27b0">Java 13</text>
    <text x="500" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2019</text>
    <line x1="430" y1="96" x2="570" y2="96" stroke="#9c27b0" stroke-width="2" />
  </g>

  <!-- === Java 14 (2020) — TOP === -->
  <g v-click>
    <line x1="514" y1="210" x2="596" y2="210" stroke="#795548" stroke-width="5" opacity="0.5" />
    <circle cx="610" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="610" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="610" cy="210" r="4" fill="#795548" />
    <line x1="610" y1="196" x2="610" y2="130" stroke="#795548" stroke-width="1.2" />
    <circle cx="610" cy="130" r="2.5" fill="#795548" />
    <text x="610" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#795548">Java 14</text>
    <text x="610" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2020</text>
    <line x1="540" y1="96" x2="680" y2="96" stroke="#795548" stroke-width="2" />
  </g>

  <!-- === Java 15 (2020) — TOP === -->
  <g v-click>
    <line x1="624" y1="210" x2="706" y2="210" stroke="#f44336" stroke-width="5" opacity="0.5" />
    <circle cx="720" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="720" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="720" cy="210" r="4" fill="#f44336" />
    <line x1="720" y1="196" x2="720" y2="130" stroke="#f44336" stroke-width="1.2" />
    <circle cx="720" cy="130" r="2.5" fill="#f44336" />
    <text x="720" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#f44336">Java 15</text>
    <text x="720" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2020</text>
    <line x1="650" y1="96" x2="790" y2="96" stroke="#f44336" stroke-width="2" />
  </g>

  <!-- === Java 16 (2021) — TOP === -->
  <g v-click>
    <line x1="734" y1="210" x2="816" y2="210" stroke="#3f51b5" stroke-width="5" opacity="0.5" />
    <circle cx="830" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="830" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="830" cy="210" r="4" fill="#3f51b5" />
    <line x1="830" y1="196" x2="830" y2="130" stroke="#3f51b5" stroke-width="1.2" />
    <circle cx="830" cy="130" r="2.5" fill="#3f51b5" />
    <text x="830" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#3f51b5">Java 16</text>
    <text x="830" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2021</text>
    <line x1="760" y1="96" x2="900" y2="96" stroke="#3f51b5" stroke-width="2" />
  </g>

  <!-- === Java 17 (2021) — BOTTOM — LTS === -->
  <g v-click>
    <line x1="844" y1="210" x2="926" y2="210" stroke="#8bc34a" stroke-width="5" opacity="0.5" />
    <circle cx="940" cy="210" r="18" fill="none" stroke="#8bc34a" stroke-width="2" />
    <circle cx="940" cy="210" r="11" fill="none" stroke="#8bc34a" stroke-width="1.1" />
    <circle cx="940" cy="210" r="5" fill="#8bc34a" />
    <line x1="940" y1="228" x2="940" y2="294" stroke="#8bc34a" stroke-width="1.2" />
    <circle cx="940" cy="294" r="2.5" fill="#8bc34a" />
    <text x="940" y="185" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#8bc34a">Java 17</text>
    <text x="940" y="319" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2021 ⭐ LTS</text>
    <line x1="860" y1="339" x2="1020" y2="339" stroke="#8bc34a" stroke-width="2" />
  </g>
</svg>

<!--
L: Oracle switched to a time-based cadence in 2017: a release every 6months. March and September, like clockwork. Every 2 years one becomes an LTS — Java 25 is the latest. Features ship when ready; the train never slips for unfinished work.
-->

---

# After 2022: The Train Keeps Moving

<svg viewBox="-30 0 1180 420" class="w-full" style="font-size: 1px;">
  <!-- Timeline: Java 18 (2022) → Java 27 (2026) -->
  <!-- Equal spacing -->
  <!-- X positions: J18→60 J19→170 J20→280 J21→390 J22→500 J23→610 J24→720 J25→830 J26→940 J27→1050 -->

  <!-- Main horizontal timeline line -->
  <line x1="30" y1="210" x2="1080" y2="210" stroke="#555" stroke-width="2" />

  <!-- === Java 18 (2022) — TOP === -->
  <g>
    <circle cx="60" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="60" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="60" cy="210" r="4" fill="#00bcd4" />
    <line x1="60" y1="196" x2="60" y2="130" stroke="#00bcd4" stroke-width="1.2" />
    <circle cx="60" cy="130" r="2.5" fill="#00bcd4" />
    <text x="60" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#00bcd4">Java 18</text>
    <text x="60" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2022</text>
    <line x1="-10" y1="96" x2="130" y2="96" stroke="#00bcd4" stroke-width="2" />
  </g>

  <!-- === Java 19 (2022) — TOP === -->
  <g v-click>
    <line x1="74" y1="210" x2="156" y2="210" stroke="#009688" stroke-width="5" opacity="0.5" />
    <circle cx="170" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="170" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="170" cy="210" r="4" fill="#009688" />
    <line x1="170" y1="196" x2="170" y2="130" stroke="#009688" stroke-width="1.2" />
    <circle cx="170" cy="130" r="2.5" fill="#009688" />
    <text x="170" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#009688">Java 19</text>
    <text x="170" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2022</text>
    <line x1="100" y1="96" x2="240" y2="96" stroke="#009688" stroke-width="2" />
  </g>

  <!-- === Java 20 (2023) — TOP === -->
  <g v-click>
    <line x1="184" y1="210" x2="266" y2="210" stroke="#ffc107" stroke-width="5" opacity="0.5" />
    <circle cx="280" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="280" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="280" cy="210" r="4" fill="#ffc107" />
    <line x1="280" y1="196" x2="280" y2="130" stroke="#ffc107" stroke-width="1.2" />
    <circle cx="280" cy="130" r="2.5" fill="#ffc107" />
    <text x="280" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#ffc107">Java 20</text>
    <text x="280" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2023</text>
    <line x1="210" y1="96" x2="350" y2="96" stroke="#ffc107" stroke-width="2" />
  </g>

  <!-- === Java 21 (2023) — BOTTOM — LTS === -->
  <g v-click>
    <line x1="294" y1="210" x2="376" y2="210" stroke="#ff9800" stroke-width="5" opacity="0.5" />
    <circle cx="390" cy="210" r="18" fill="none" stroke="#ff9800" stroke-width="2" />
    <circle cx="390" cy="210" r="11" fill="none" stroke="#ff9800" stroke-width="1.1" />
    <circle cx="390" cy="210" r="5" fill="#ff9800" />
    <line x1="390" y1="228" x2="390" y2="294" stroke="#ff9800" stroke-width="1.2" />
    <circle cx="390" cy="294" r="2.5" fill="#ff9800" />
    <text x="390" y="185" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#ff9800">Java 21</text>
    <text x="390" y="319" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2023 ⭐ LTS</text>
    <line x1="310" y1="339" x2="470" y2="339" stroke="#ff9800" stroke-width="2" />
  </g>

  <!-- === Java 22 (2024) — TOP === -->
  <g v-click>
    <line x1="404" y1="210" x2="486" y2="210" stroke="#e91e63" stroke-width="5" opacity="0.5" />
    <circle cx="500" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="500" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="500" cy="210" r="4" fill="#e91e63" />
    <line x1="500" y1="196" x2="500" y2="130" stroke="#e91e63" stroke-width="1.2" />
    <circle cx="500" cy="130" r="2.5" fill="#e91e63" />
    <text x="500" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#e91e63">Java 22</text>
    <text x="500" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2024</text>
    <line x1="430" y1="96" x2="570" y2="96" stroke="#e91e63" stroke-width="2" />
  </g>

  <!-- === Java 23 (2024) — TOP === -->
  <g v-click>
    <line x1="514" y1="210" x2="596" y2="210" stroke="#673ab7" stroke-width="5" opacity="0.5" />
    <circle cx="610" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="610" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="610" cy="210" r="4" fill="#673ab7" />
    <line x1="610" y1="196" x2="610" y2="130" stroke="#673ab7" stroke-width="1.2" />
    <circle cx="610" cy="130" r="2.5" fill="#673ab7" />
    <text x="610" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#673ab7">Java 23</text>
    <text x="610" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2024</text>
    <line x1="540" y1="96" x2="680" y2="96" stroke="#673ab7" stroke-width="2" />
  </g>

  <!-- === Java 24 (2025) — TOP === -->
  <g v-click>
    <line x1="624" y1="210" x2="706" y2="210" stroke="#4caf50" stroke-width="5" opacity="0.5" />
    <circle cx="720" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="720" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="720" cy="210" r="4" fill="#4caf50" />
    <line x1="720" y1="196" x2="720" y2="130" stroke="#4caf50" stroke-width="1.2" />
    <circle cx="720" cy="130" r="2.5" fill="#4caf50" />
    <text x="720" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#4caf50">Java 24</text>
    <text x="720" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2025</text>
    <line x1="650" y1="96" x2="790" y2="96" stroke="#4caf50" stroke-width="2" />
  </g>

  <!-- === Java 25 (2025) — BOTTOM — LTS === -->
  <g v-click>
    <line x1="734" y1="210" x2="816" y2="210" stroke="#f44336" stroke-width="5" opacity="0.5" />
    <circle cx="830" cy="210" r="18" fill="none" stroke="#f44336" stroke-width="2" />
    <circle cx="830" cy="210" r="11" fill="none" stroke="#f44336" stroke-width="1.1" />
    <circle cx="830" cy="210" r="5" fill="#f44336" />
    <line x1="830" y1="228" x2="830" y2="294" stroke="#f44336" stroke-width="1.2" />
    <circle cx="830" cy="294" r="2.5" fill="#f44336" />
    <text x="830" y="185" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#f44336">Java 25</text>
    <text x="830" y="319" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2025 ⭐ LTS</text>
    <line x1="750" y1="339" x2="910" y2="339" stroke="#f44336" stroke-width="2" />
  </g>

  <!-- === Java 26 (2026) — TOP === -->
  <g v-click>
    <line x1="844" y1="210" x2="926" y2="210" stroke="#3f51b5" stroke-width="5" opacity="0.5" />
    <circle cx="940" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="940" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="940" cy="210" r="4" fill="#3f51b5" />
    <line x1="940" y1="196" x2="940" y2="130" stroke="#3f51b5" stroke-width="1.2" />
    <circle cx="940" cy="130" r="2.5" fill="#3f51b5" />
    <text x="940" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#3f51b5">Java 26</text>
    <text x="940" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">March 2026</text>
    <line x1="870" y1="96" x2="1010" y2="96" stroke="#3f51b5" stroke-width="2" />
  </g>

  <!-- === Java 27 (2026) — TOP === -->
  <g v-click>
    <line x1="954" y1="210" x2="1036" y2="210" stroke="#8bc34a" stroke-width="5" opacity="0.5" />
    <circle cx="1050" cy="210" r="14" fill="none" stroke="#666" stroke-width="1.2" />
    <circle cx="1050" cy="210" r="9" fill="none" stroke="#666" stroke-width="0.8" />
    <circle cx="1050" cy="210" r="4" fill="#8bc34a" />
    <line x1="1050" y1="196" x2="1050" y2="130" stroke="#8bc34a" stroke-width="1.2" />
    <circle cx="1050" cy="130" r="2.5" fill="#8bc34a" />
    <text x="1050" y="243" text-anchor="middle" style="font-size: 26px; font-weight: bold;" fill="#8bc34a">Java 27</text>
    <text x="1050" y="120" text-anchor="middle" style="font-size: 18px;" fill="white">Sep 2026</text>
    <line x1="980" y1="96" x2="1120" y2="96" stroke="#8bc34a" stroke-width="2" />
  </g>
</svg>

<!--
L:
Non-LTS releases like Java 26 still matter: early access to final and preview features without multi-year waits.
-->

---

<div class="quote-slide">
  <div class="quote-text">
    This helps Java remain competitive […] while maintaining its core values of compatibility and reliability.
  </div>
  <div class="quote-attr">— Mark Reinhold</div>
</div>

<!--
Lutske:
Mark Reinhold captured the goal: stay competitive while protecting compatibility and reliability. This mindset is why the release train works , progress without surprises.
-->

---

# Java 26 + 27: What shipped as Final

<div class="mt-2 text-sm">

| JEP | Feature | Version |
|-----|---------|---------|
| 500 | Prepare to Make Final Mean Final | <Badge26/> |
| 504 | Remove the Applet API | <Badge26/> |
| 516 | Ahead-of-Time Object Caching with Any GC | <Badge26/> |
| 517 | HTTP/3 for the HTTP Client API | <Badge26/> |
| 522 | G1 GC: Improve Throughput | <Badge26/> |
| 523 | G1 GC: Now Default on All Systems | <Badge27/> |
| 534 | Compact Object Headers: Now Default | <Badge27/> |
| 536 | JFR In-Process Data Redaction | <Badge27/> |

</div>

<!--
Lutske:
Here’s what shipped as final across Java 26 and 27.
Five finals in Java 26. Java 27 adds G1 as universal default, compact headers as default, JFR redaction, and post-quantum TLS.
-->

---

# Java 26 + 27: Preview & Incubating

<div class="mt-2 text-sm">

| JEP | Feature | Status | Version |
|-----|---------|--------|---------|
| 525/533 | Structured Concurrency | <Badge variant="blue">6th → 7th Preview</Badge> | <Badge variant="teal">26+27</Badge> |
| 526/531 | Lazy Constants | <Badge variant="blue">2nd → 3rd Preview</Badge> | <Badge variant="teal">26+27</Badge> |
| 529/537 | Vector API | <Badge variant="gray">11th → 12th Incubator</Badge> | <Badge variant="teal">26+27</Badge> |
| 530/532 | Primitive Types in Patterns | <Badge variant="blue">4th → 5th Preview</Badge> | <Badge variant="teal">26+27</Badge> |

</div>

<!--
Johannes:
The preview features all advanced — same pattern across both releases.
We’ll dig into each of these.
-->

---

# Java 26 + 27: Cryptography

<div class="mt-2 text-sm">

| JEP | Feature | Status | Version |
|-----|---------|--------|---------|
| 524 | PEM Encodings of Cryptographic Objects | <Badge variant="blue">2nd Preview</Badge> | <Badge variant="teal">26+27</Badge> |
| 527 | Post-Quantum Hybrid Key Exchange for TLS 1.3 | <Badge variant="green">Final</Badge> | <Badge27/> |
| 538 | PEM Encodings of Cryptographic Objects | <Badge variant="blue">3rd Preview</Badge> | <Badge variant="teal">26+27</Badge> |

</div>

<!--
Johannes:
Two dedicated crypto JEPs, plus eight more under the surface.
PEM encodings advancing toward final. Post-quantum TLS shipping in Java 27 by default — zero config needed.
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

<span class="text-emerald">`final`</span> will <span class="text-emerald">finally</span> mean <span class="text-emerald">final</span>.

</div>

<div class="text-xl mt-8">

JEP 500: Prepare to Make Final Mean Final

</div>

</div>

<!--
Lutske
-->

---

# What reflection hacks look like today

<CodeRunner slide-id="reflection-hack" :indent=4>

  <template #before>
  
```java
void main() throws java.lang.Exception {
```

  </template>
  <template #default>

```java
// This works today — but it shouldn't
class Config {
    private final String secret = "original";
}

var config = new Config();
var field = Config.class.getDeclaredField("secret");
field.setAccessible(true);
field.set(config, "hacked");  // ← final? What final?
```

  </template>

  <template #after>
  
```java
}
```

  </template>
</CodeRunner>

<v-click>

<div class="text-xl mt-6">

⚠️ **Java 26**: runtime warning<br/>
🚫 **Future release**: blocked entirely

</div>

</v-click>

<!--
Lutske
-->

---
layout: section
---


<div class="relative z-10">

# The Invisible <br/> GC Upgrade

JEP 522 <Badge26/> · JEP 523 <Badge27/>

</div>

<!--
Lutske:
Invisible improvements are my favorite: do nothing and your app gets faster. G1 has been the default since Java 9; this JEP reduces synchronization between your app and the GC.
-->

---
layout: center
---

<div class="relative z-10">

<div class="text-8xl font-bold text-emerald-400">

5–15%

</div>

<div class="text-2xl text-gray-300 mt-6">

more throughput. For free.


<small>*According to the JEP 522.*</small>


</div>

</div>

<!--
Lutske
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

Zero lines of code changed. <br/>Just upgrade your JDK.

</div>

<div class="text-3xl text-emerald mt-8 text-center">

This is what <BlueText>boring</BlueText> looks like in practice.

</div>

</div>

<!--
Lutske
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

Java 27: G1 is now the default <br/> <span class="text-7xl text-blue-500">everywhere.</span>

</div>

<div class="text-xl text-gray-300 mt-8">

**JEP 523** — Previously, Serial GC was chosen for single-CPU or memory-constrained systems.<br/>
The JDK 26 throughput improvements made that distinction unnecessary.

</div>

</div>

<!--
Lutske
-->

---
layout: section
---

<div class="relative z-10">

# Ahead of Time Compilation

JEP 516 <Badge26/>

</div>

<!--
Johannes
-->

---

# AOT Object Caching — now with Any GC

<div class="mt-4">

```shell
# Training run: JVM records startup objects
java -XX:AOTCacheOutput=app.aot -jar myapp.jar

# Production: loads pre-built objects instead
java -XX:AOTCache=app.aot -jar myapp.jar
```

</div>

<v-click>

<div class="mt-5 grid grid-cols-3 gap-4 text-center">
  <div class="bg-zinc-800 rounded-lg p-3">
    <div class="text-3xl font-bold text-emerald-400">~40%</div>
    <div class="text-sm text-gray-400 mt-1">faster startup</div>
  </div>
  <div class="bg-zinc-800 rounded-lg p-3">
    <div class="text-3xl font-bold text-emerald-400">~40%</div>
    <div class="text-sm text-gray-400 mt-1">less startup memory</div>
  </div>
  <div class="bg-zinc-800 rounded-lg p-3">
    <div class="text-3xl font-bold text-emerald-400">0</div>
    <div class="text-sm text-gray-400 mt-1">lines of app code changed</div>
  </div>
</div>

</v-click>

<!--
Johannes

Lutske shouts in Boring

J: "AOT Object Caching — the JVM remembers your startup work and skips it next time. Training run once, then load the cache in production."
L: "40% faster startup, 40% less memory at startup. Zero application code changes."
J: "Now works with any GC — ZGC, Shenandoah, Parallel. Previously G1 only."
-->

---
layout: section
---


<div class="relative z-10">

# HTTP/3 in the Standard Library

JEP 517 <Badge26/>

</div>

<!--
L: "Next up: HTTP/3 — the latest version of the web's protocol. It's built on QUIC over UDP with TLS 1.3 baked in. That means faster connection setup, no head-of-line blocking, and better behavior on unreliable networks."
-->

---
layout: center
---

<div class="relative w-full max-w-2xl mx-auto">

<v-click>

<div class="mb-10">
  <div class="flex items-center gap-3 mb-2">
    <span class="text-2xl font-bold text-amber-400">HTTP/1.1</span>
    <span class="text-gray-400 text-lg">— One lane road. One request at a time.</span>
  </div>
  <div class="relative h-12 bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
    <div class="absolute top-0 left-0 w-full h-full flex items-center">
      <div class="h-[2px] w-full bg-gray-600 absolute top-1/2"></div>
      <div class="absolute animate-car-slow">
        <span class="text-2xl">🚗</span>
      </div>
    </div>
  </div>
</div>

</v-click>

<v-click>

<div class="mb-10">
  <div class="flex items-center gap-3 mb-2">
    <span class="text-2xl font-bold text-blue-400">HTTP/2</span>
    <span class="text-gray-400 text-lg">— Multi-lane highway. Multiplexed streams.</span>
  </div>
  <div class="relative h-20 bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
    <div class="absolute top-0 left-0 w-full h-full flex flex-col justify-around py-2">
      <div class="relative h-[2px] bg-gray-600"><div class="absolute animate-car-fast1"><span class="text-xl">🚙</span></div></div>
      <div class="relative h-[2px] bg-gray-600"><div class="absolute animate-car-fast2"><span class="text-xl">🚕</span></div></div>
      <div class="relative h-[2px] bg-gray-600"><div class="absolute animate-car-fast3"><span class="text-xl">🚗</span></div></div>
    </div>
  </div>
</div>

</v-click>

<v-click>

<div class="mb-4">
  <div class="flex items-center gap-3 mb-2">
    <span class="text-2xl font-bold text-emerald-400">HTTP/3</span>
    <span class="text-gray-400 text-lg">— No road at all. Just fly. <em class="text-emerald-600"> (QUIC over UDP)</em></span>
  </div>
  <div class="relative h-20 bg-gradient-to-r from-gray-800 via-sky-950 to-gray-800 rounded-lg overflow-hidden border border-sky-900">
    <div class="absolute top-0 left-0 w-full h-full">
      <div class="absolute animate-plane1"><span class="text-2xl">✈️</span></div>
      <div class="absolute animate-plane2"><span class="text-xl">✈️</span></div>
      <div class="absolute animate-plane3"><span class="text-2xl">✈️</span></div>
      <div class="absolute animate-plane4"><span class="text-lg">✈️</span></div>
      <div class="absolute animate-plane5"><span class="text-xl">✈️</span></div>
      <div class="absolute animate-plane6"><span class="text-lg">✈️</span></div>
      <div class="absolute animate-plane7"><span class="text-2xl">✈️</span></div>
      <div class="absolute animate-plane8"><span class="text-xl">✈️</span></div>
      <div class="absolute animate-plane9"><span class="text-lg">✈️</span></div>
      <div class="absolute animate-plane10"><span class="text-xl">✈️</span></div>
      <div class="absolute w-full h-full opacity-20">
        <div class="absolute top-2 left-[15%] text-white text-xs">☁️</div>
        <div class="absolute top-8 left-[40%] text-white text-xs">☁️</div>
        <div class="absolute top-1 left-[65%] text-white text-xs">☁️</div>
        <div class="absolute top-10 left-[85%] text-white text-xs">☁️</div>
      </div>
    </div>
  </div>
</div>

</v-click>

</div>


<!--
L: "HTTP/1.1 was a single-lane road: one request, one response, wait."
[click]
"HTTP/2 multiplexed like a multi-lane highway."
[click]
"HTTP/3 threw out the road entirely. Built on QUIC over UDP — faster setup, no head-of-line blocking. It basically flies."
-->

---

# Using HTTP/3 in Java 26

<CodeRunner slide-id="http3-example" enable-preview :indent=4>

  <template #before>
  
```java
import java.net.http.*;
import java.net.*;

void main() throws Exception {
```

  </template>
  <template #default>

```java
var client = HttpClient.newBuilder()
    .version(HttpClient.Version.HTTP_3)  // ← just add this
    .build();

var request = HttpRequest.newBuilder()
    .uri(URI.create("https://example.com/api"))
    .build();

var response = client.send(request,
    HttpResponse.BodyHandlers.ofString());
    
System.out.println("Status: " + response.statusCode());
System.out.println("Body: " + response.body().substring(0, Math.min(100, response.body().length())) + "...");
```

  </template>

  <template #after>
  
```java

}
```

  </template>
</CodeRunner>

<!--
Lutske
-->

---
layout: center
---

<div class="relative z-10 flex items-center justify-center h-full">

<div class="quote-slide">
  <div class="quote-text">
    "You'll be fine without it. HTTP/2 is good enough."
  </div>
<div class="quote-attr">— Unnamed Netty Developer</div>
</div>

</div>

<!--
Lutske
-->

---
layout: section
---

<div class="relative z-10">

# Cryptography

JEP 524/538 <Badge variant="teal">26+27</Badge> · JEP 527 <Badge27/>

</div>

<!--
Johannes
J: "While we're in the networking and security space — Java 26 and 27 bring significant cryptography improvements."
-->

---

# PEM Encodings <Badge variant="blue">2nd Preview (Java 26)</Badge> <Arrow/> <Badge variant="blue">3rd Preview (Java 27)</Badge>

<div class="mt-6 text-lg">

**JEP 524** (Java 26) · **JEP 538** (Java 27)

</div>

<div class="mt-4">

```java
// Read a PEM-encoded certificate
PEMDecoder decoder = PEMDecoder.of();
X509Certificate cert = (X509Certificate)
    decoder.decode(Files.readString(Path.of("server.pem")));

// Write a key as PEM
PEMEncoder encoder = PEMEncoder.of();
String pem = encoder.encodeToString(keyPair.getPrivate());
```

</div>

<div class="mt-6 text-lg text-gray-300">

PEM is the universal format for certificates and keys — <code>.pem</code>, <code>.crt</code>, <code>.key</code> files everywhere.
Previously required third-party libraries (BouncyCastle). Now it's in the JDK.

</div>

<!--
Johannes
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

Post-Quantum TLS

</div>

<div class="text-xl text-gray-300 mt-8">

**JEP 527** <Badge27/> — Hybrid key exchange in TLS 1.3<br/>
Classical (X25519) + Post-Quantum (ML-KEM) in one handshake.<br/><br/>
You don't change a single line of code.<br/>Java 27 just protects you.

</div>

</div>

<!--
Johannes
-->

---
layout: center
---

<div class="relative z-10">

<div class="text-4xl font-bold text-emerald-400 mb-8">+8 more crypto fixes</div>

<div class="text-xl text-gray-300 leading-loose text-left max-w-xl mx-auto">

Eight separate JDK issues improved in Java 27 — key derivation, algorithm providers, cipher edge cases, TLS compression (zlib) support.

<div class="mt-6 text-2xl text-emerald">

Boring maintenance. That matters.

</div>

</div>

</div>

<!--
Johannes
-->

---
layout: center
---

<div class="relative z-10">

# A moment of silence please
<v-click>

<div class="max-w-md mx-auto">
  <CroppedImage src="./img/java-applet.png"/>
</div>
</v-click>

</div>

<!--
Lutske:
-->

---

# The rise and fall of Java applets

<svg viewBox="-25 0 535 300" class="w-full" style="font-size: 1px;">
  <!-- Timeline spans 1995–2026 (31 years). X positions proportional to time -->
  <!-- Compressed: 1995→15  2013→280  2017→335  2026→470 -->

  <!-- Main horizontal timeline line -->
  <line x1="15" y1="145" x2="470" y2="145" stroke="#555" stroke-width="1.3" />

  <!-- === 1995: Applets ship (BOTTOM) === -->
<g>
  <circle cx="15" cy="145" r="8" fill="none" stroke="#666" stroke-width="0.8" />
  <circle cx="15" cy="145" r="5.5" fill="none" stroke="#666" stroke-width="0.5" />
  <circle cx="15" cy="145" r="2" fill="#00bcd4" />
  <line x1="15" y1="153" x2="15" y2="195" stroke="#00bcd4" stroke-width="0.8" />
  <circle cx="15" cy="195" r="1.2" fill="#00bcd4" />
  <text x="15" y="132" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#00bcd4">1995</text>
  <text x="15" y="208" text-anchor="middle" style="font-size: 10px;" fill="white">Ships 🎉</text>
  <line x1="-12" y1="220" x2="42" y2="220" stroke="#00bcd4" stroke-width="2" />
  </g>

  <!-- === 2013: Browsers drop (TOP) === -->
  <g v-click>
  <circle cx="280" cy="145" r="8" fill="none" stroke="#666" stroke-width="0.8" />
  <circle cx="280" cy="145" r="5.5" fill="none" stroke="#666" stroke-width="0.5" />
  <circle cx="280" cy="145" r="2" fill="#2196f3" />
  <line x1="280" y1="137" x2="280" y2="100" stroke="#2196f3" stroke-width="0.8" />
  <circle cx="280" cy="100" r="1.2" fill="#2196f3" />
  <text x="280" y="161" text-anchor="middle" style="font-size: 13px; font-weight: bold;" fill="#2196f3">2013</text>
  <text x="280" y="92" text-anchor="middle" style="font-size: 10px;" fill="white">Browsers drop support</text>
  <line x1="218" y1="77" x2="342" y2="77" stroke="#2196f3" stroke-width="2" />
  </g>

  <!-- === 2017: Deprecated (BOTTOM) === -->
  <g v-click>
  <circle cx="335" cy="145" r="8" fill="none" stroke="#666" stroke-width="0.8" />
  <circle cx="335" cy="145" r="5.5" fill="none" stroke="#666" stroke-width="0.5" />
  <circle cx="335" cy="145" r="2" fill="#607d8b" />
  <line x1="335" y1="153" x2="335" y2="195" stroke="#607d8b" stroke-width="0.8" />
  <circle cx="335" cy="195" r="1.2" fill="#607d8b" />
  <text x="335" y="132" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#607d8b">2017</text>
  <text x="335" y="208" text-anchor="middle" style="font-size: 10px;" fill="white">Deprecated ⚠️</text>
  <line x1="293" y1="220" x2="377" y2="220" stroke="#607d8b" stroke-width="2" />
  </g>

  <!-- === 2026: Removed (TOP) === -->
  <g v-click>
  <circle cx="470" cy="145" r="8" fill="none" stroke="#666" stroke-width="0.8" />
  <circle cx="470" cy="145" r="5.5" fill="none" stroke="#666" stroke-width="0.5" />
  <circle cx="470" cy="145" r="2" fill="#9e9e9e" />
  <line x1="470" y1="137" x2="470" y2="100" stroke="#9e9e9e" stroke-width="0.8" />
  <circle cx="470" cy="100" r="1.2" fill="#9e9e9e" />
  <text x="470" y="161" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#9e9e9e">2026</text>
  <text x="470" y="92" text-anchor="middle" style="font-size: 10px;" fill="white">Removed 🪦</text>
  <line x1="435" y1="77" x2="505" y2="77" stroke="#9e9e9e" stroke-width="2" />
  </g>
</svg>

<!--
Lutske
-->

---

# A code tombstone

<div class="compact-code mt-4">

```html
<!-- This used to be a thing. Seriously. -->
<applet code="HelloApplet.class" archive="hello-applet.jar"
        width="300" height="120">
  Your browser does not support Java applets.
</applet>
```

</div>

<v-click>

<div class="mt-6">

```java
public class HelloApplet extends Applet {
    @Override
    public void paint(Graphics g) {
        g.drawString("Hello from 1997!", 20, 40);
    }
}
```

</div>

</v-click>

<v-click>

<div class="text-xl mt-6">

The `java.applet` package and `JApplet` are now gone. 🪦

</div>

</v-click>

<!--
Lutske
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

What applets teach us about Java

</div>

<div class="mt-8 text-xl leading-loose">

📢 **Signal early** — deprecated in Java 9 (2017)

⏳ **Remove slowly** — 9 years of warnings

💥 **Break nothing** — zero practical impact when finally removed

</div>

<v-click>

<div class="text-3xl mt-9">

This is the pattern. This is how <span class="text-emerald">boring</span> works.

</div>

</v-click>

</div>

<!--
Lutske
-->

---
layout: section
---

<div class="relative z-10">

# Java 27: One more 
# moment of silence

</div>

<!--
Johannes
-->

---
layout: center
---

<div class="slide-content flex flex-col items-center justify-center h-full">

<div class="flex flex-col items-center gap-6">
  <img src="https://mostlynerdless.de/wp-content/uploads/2026/09/ChatGPT-Image-Sep-14-2026-05_19_33-PM.png"
       class="h-140 object-contain rounded-lg" alt="JVMCI gravestone" />
</div>

</div>

<!--
Johannes
-->

---

# The JVMCI story

<svg viewBox="-25 0 535 300" class="w-full" style="font-size: 1px;">
  <!-- Axis at y=145, spans x=15..470 -->
  <line x1="15" y1="145" x2="470" y2="145" stroke="#475569" stroke-width="1.3"/>

  <!-- 2016: Introduced — ABOVE -->
  <circle cx="60" cy="145" r="6" fill="none" stroke="#8b5cf6" stroke-width="0.8"/>
  <circle cx="60" cy="145" r="3" fill="#8b5cf6"/>
  <line x1="60" y1="137" x2="60" y2="100" stroke="#8b5cf6" stroke-width="0.8"/>
  <circle cx="60" cy="100" r="1.2" fill="#8b5cf6"/>
  <text x="60" y="160" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#c4b5fd">2016</text>
  <text x="60" y="92" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">JEP 243: JVMCI</text>
  <text x="60" y="79" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">GraalVM JIT hook</text>
  <line x1="18" y1="68" x2="102" y2="68" stroke="#8b5cf6" stroke-width="1.5"/>

  <!-- 2019: GraalVM CE — BELOW -->
  <circle cx="190" cy="145" r="6" fill="none" stroke="#6366f1" stroke-width="0.8"/>
  <circle cx="190" cy="145" r="3" fill="#6366f1"/>
  <line x1="190" y1="153" x2="190" y2="195" stroke="#6366f1" stroke-width="0.8"/>
  <circle cx="190" cy="195" r="1.2" fill="#6366f1"/>
  <text x="190" y="132" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#a5b4fc">2019</text>
  <text x="190" y="208" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">GraalVM CE ships</text>
  <text x="190" y="220" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">JVMCI at its peak</text>
  <line x1="142" y1="232" x2="238" y2="232" stroke="#6366f1" stroke-width="1.5"/>

  <!-- 2022: Separation — ABOVE -->
  <circle cx="330" cy="145" r="6" fill="none" stroke="#f59e0b" stroke-width="0.8"/>
  <circle cx="330" cy="145" r="3" fill="#f59e0b"/>
  <line x1="330" y1="137" x2="330" y2="100" stroke="#f59e0b" stroke-width="0.8"/>
  <circle cx="330" cy="100" r="1.2" fill="#f59e0b"/>
  <text x="330" y="160" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#fcd34d">2022</text>
  <text x="330" y="92" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">Oracle separates GraalVM</text>
  <text x="330" y="79" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">Primary use case gone</text>
  <line x1="272" y1="68" x2="388" y2="68" stroke="#f59e0b" stroke-width="1.5"/>

  <!-- Java 27: Removed — BELOW -->
  <circle cx="440" cy="145" r="6" fill="none" stroke="#ef4444" stroke-width="0.8"/>
  <circle cx="440" cy="145" r="3" fill="#ef4444"/>
  <line x1="440" y1="153" x2="440" y2="195" stroke="#ef4444" stroke-width="0.8"/>
  <circle cx="440" cy="195" r="1.2" fill="#ef4444"/>
  <text x="440" y="132" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#fca5a5">Java 27</text>
  <text x="440" y="208" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">JVMCI removed</text>
  <text x="440" y="220" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">252 #if blocks eliminated</text>
  <line x1="394" y1="232" x2="476" y2="232" stroke="#ef4444" stroke-width="1.5"/>
</svg>

<div class="mt-2 text-sm text-gray-400">

Affected: GraalJS, JRuby, TornadoVM — TornadoVM has since replaced the underlying technology.

</div>

<!--
Johannes
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

What JVMCI teaches us

</div>

<div class="mt-8 text-xl leading-loose">

📢 **Architecture follows strategy** — when the strategy changes, the code changes

⏳ **Maintenance debt accumulates** — 252 conditionals across the JDK

💥 **Removal is a feature** — a cleaner JDK is a faster, safer JDK

</div>

<v-click>

<div class="text-3xl mt-9">

This is how <span class="text-emerald">boring</span> works.

</div>

</v-click>

</div>

<!--
Johannes
-->

---
layout: section
---

<div class="relative z-10">

# Preview & Incubating Features

The features that aren't ready yet — and that's okay

</div>

<!--
Lutske
-->

---

# Primitive types in patterns <Badge variant="blue">4th Preview</Badge> <Badge26/> <Arrow/> <Badge variant="blue">5th Preview</Badge> <Badge27/>

<CodeRunner slide-id="primitive-patterns" enable-preview :indent=4>

  <template #before>
  
```java
void main() {
```

  </template>
  <template #default>

```java
// Pattern matching now works with primitive types
Object value = 42;

String result = switch (value) {
    case int i when i > 0    -> "positive: " + i;
    case int i when i < 0    -> "negative: " + i;
    case int i               -> "zero";
    case long l              -> "long: " + l;
    case double d            -> "double: " + d;
    default                  -> "something else";
};

System.out.println(result);
```

  </template>

  <template #after>
  
```java
}
```

  </template>
</CodeRunner>

<!--
Lutske
-->

---

# Java Puzzler
<Caption> by Cay Horstmann</Caption>


<CodeRunner enable-preview>

```java {5|6|7||all}
record Amount(Number n) {}

Integer value(Amount p) {
    return switch (p) {
        case Amount(int value) -> value;
        case Amount(Number _) -> -1;
        case Amount(Object _) -> -2;
    };
}

void main() {
    System.out.println(value(new Amount(null)));
}
```

</CodeRunner>

<div class="text-base mt-6 flex gap-6 justify-center flex-wrap font-medium">

<div>A) <code>null</code> </div>
<div>B) <code>-1</code></div>
<div>C) <code>-2</code></div>
<div>D) Exception</div>

</div>

<!--
Lutske
-->

---

# Lazy constants <Badge variant="blue">JEP 526, 2nd Preview</Badge> <Badge26/> → <Badge variant="blue">JEP 531, 3rd Preview</Badge> <Badge27/>

<div class="mt-8">

<CodeRunner slide-id="lazy-constant" enable-preview :indent=4>
  <template #before>

```java
import java.util.function.Supplier;

class ExpensiveService {
    ExpensiveService() {
        System.out.println("ExpensiveService created!");
    }
    void doWork() {
        System.out.println("Doing work...");
    }
}

void main() {
```

  </template>
  <template #default>

```java
    // Initialized only when first accessed — thread-safe, immutable
    Supplier<ExpensiveService> SERVICE =
        LazyConstant.of(() -> {
            System.out.println("Initializing...");
            return new ExpensiveService();
        });

    System.out.println("LazyConstant created (not yet initialized)");
    
    // First call triggers initialization
    var service = SERVICE.get();

    // All subsequent calls return the cached value
    var service2 = SERVICE.get();
```

  </template>
  <template #after>

```java
}
```

  </template>
</CodeRunner>

</div>

<v-click>
<div class="mt-4">
Could you implement it yourself? Yes.

<div class="text-3xl mt-4 text-green">
Boring.
</div>
</div>
</v-click>

<!--
Johannes:
-->

---
layout: center
---

<div class="relative z-10 flex flex-col items-center justify-center h-full max-w-3xl mx-auto text-center">

<div class="text-2xl text-purple-300 font-semibold mb-6">Why rename StableValue → LazyConstant?</div>

<div class="quote-slide" style="padding: 0;">
  <div class="quote-text" style="font-size: 1.4rem;">
    "We renamed the API from StableValue to LazyConstant. The former was appropriate for a low-level API that was close to the underlying JVM mechanism upon which it is implemented; the latter better captures the primary intended high-level use case, namely that of a single constant value that is initialized lazily."
  </div>
  <div class="quote-attr">— JEP 531</div>
</div>

</div>

<!--
Johannes
-->

---
layout: center
---

<div class="relative z-10 flex flex-col items-center justify-center h-full">

<div class="big-statement">
Preview features might<br/>change or <RedText>disappear</RedText>.
</div>

<v-click>

<div class="text-3xl mt-8 text-gray-400">
Remember <span class="text-red-400 font-bold">string templates</span>?
</div>

</v-click>

</div>

<!--
Johannes
-->

---

# Structured concurrency <Badge variant="blue">6th</Badge> <Badge26/> <Arrow/> <Badge variant="blue">7th</Badge> <Badge27/> <Arrow/> <Badge28/>

<div class="compact-code grid grid-cols-2 gap-4 mt-6">
<div>

**Java 8: manual**

<CodeRunner slide-id="structured-concurrency-old" enable-preview :indent=4>

  <template #before>
  
```java
import java.util.concurrent.*;

String fetch(String source) {
    try { Thread.sleep(100); } catch (Exception e) {}
    return "Data from " + source;
}

void main() throws Exception {
```

  </template>
  <template #default>

```java
ExecutorService es =
  Executors.newFixedThreadPool(2);

Future<String> f1 =
  es.submit(() -> fetch("left"));
Future<String> f2 =
  es.submit(() -> fetch("right"));

String r = f1.get() + f2.get();
es.shutdown();

System.out.println(r);
```

  </template>

  <template #after>
  
```java
}
```

  </template>
</CodeRunner>

</div>
<div>

**Java 26: structured**

<CodeRunner slide-id="structured-concurrency-new" enable-preview :indent=4>

  <template #before>
  
```java
import java.util.concurrent.*;

String fetch(String source) {
    try { Thread.sleep(100); } catch (Exception e) {}
    return "Data from " + source;
}

void main() throws Exception {
```

  </template>
  <template #default>

```java
try (var scope = StructuredTaskScope.open()) {

  var f1 = scope.fork(
    () -> fetch("left"));
  var f2 = scope.fork(
    () -> fetch("right"));

  scope.join();
  
  String r = f1.get() + " | " + f2.get();
  
  System.out.println(r);
}
```

  </template>

  <template #after>
  
```java
}
```

  </template>
</CodeRunner>

</div>
</div>

<!--
Lutske
-->

---

# Vector API <Badge variant="gray">11th Incubator</Badge> <Badge26/> <Arrow/> <Badge variant="gray">12th Incubator</Badge> <Badge27/>

<div class="mt-8">

<CodeRunner slide-id="vector-api" enable-preview :indent=4 add-modules="jdk.incubator.vector">
  <template #before>

```java
import jdk.incubator.vector.*;

void main() {
```

  </template>
  <template #default>

```java
    // SIMD: process multiple data points in a single CPU instruction
    VectorSpecies<Float> SPECIES = FloatVector.SPECIES_PREFERRED;

    float[] a = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f};
    float[] b = {1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
    float[] result = new float[a.length];

    // Vector addition using SIMD
    for (int i = 0; i < a.length; i += SPECIES.length()) {
        var va = FloatVector.fromArray(SPECIES, a, i);
        var vb = FloatVector.fromArray(SPECIES, b, i);
        va.add(vb).intoArray(result, i);
    }

    System.out.println("Result: " + java.util.Arrays.toString(result));
```

  </template>
  <template #after>

```java
}
```

  </template>
</CodeRunner>

</div>

<!--
Lutske
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

  You <RedText>don't</RedText> need these yet.<br/>
<span class="text-2xl">They're <BlueText>preview</BlueText> for a reason.</span> <br/>
  <span class="text-3xl">But please try them and give feedback. <br/>That's how they graduate.</span>

</div>

</div>

<!--
Lutske
-->

---

# How to try preview features

<div class="mt-8">

```shell
# Compile with preview features enabled
javac --enable-preview --release 27 MyApp.java

# Run with preview features enabled
java --enable-preview MyApp
```

</div>

<!--
Lutske
-->

---
layout: section
---

<div class="relative z-10">

# Who are these features
#  really for?

Library developers — and why that matters to you

</div>

<!--
Johannes:
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

OpenJDK: Not <BlueText>one</BlueText> company

</div>

<div class="mt-8 text-lg leading-loose">

<v-click>

Many distributions.

All free. All TCK-tested. All interchangeable.

</v-click>

</div>

</div>

<!--
Johannes:
-->

---

<CroppedImage src="./img/java_25_contributions.avif" alt="Java contributors" />
<ImageAttribution>
  Oracle
</ImageAttribution>

<!--
Johannes
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

Your skills don't <RedText>expire</RedText>.

</div>

<div class="text-xl mt-8">

A developer who learned Java in 2005 writes modern Java today.

</div>

</div>

<!--
Johannes
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

"It works on Java 8"<br/>is not a strategy.

</div>

<v-click>

<div class="text-xl text-gray-400 mt-8">

It's technical debt with a smiley face.

</div>

</v-click>

</div>

<!--
Johannes
-->

---

<div class="quote-slide">
  <div class="quote-text">
    "There is a small but immediate cost of upgrading. There is a huge, potentially catastrophic but not immediate cost of staying on old versions. Until the disasters become visible, people don't want to invest.<br/><br/>Sounds a bit like climate change."
  </div>
  <div class="quote-attr">— Johan Vos</div>
</div>

<!--
Lutske
-->

---

<div class="relative z-10">

# Honest moment: what Java still lacks

<div class="mt-8 text-3xl leading-loose">

<v-click>❌ String interpolation</v-click><br/>

<v-click>❌ Null safety</v-click><v-click><span style="font-size: 0.5em; color: gray;"> maybe with Valhalla</span></v-click><br/>

<v-click>❌ Simpler concurrency</v-click><v-click> <span style="font-size: 0.5em; color: gray;">. Structured Concurrency, JDK 28</span></v-click><br/>

<v-click>❌ Commas after last argument</v-click><br/>

<v-click>❌ No JSON built-in</v-click><v-click><span style="font-size: 0.5em; color: gray;"> Preview coming in JDK 28</span></v-click><br/>

</div>

<v-click>

<div class="text-lg mt-6">

Java is not perfect. We're not here to pretend it is.

</div>

</v-click>

<v-click>

<div class="text-3xl mt-6">

It's <span class="text-emerald">boring</span>.

</div>

</v-click>

</div>

<!--
Lutske
mention that Java 28 brings JSON builtin preview, null safety potentially partially with Valhalla
simpler concurrency
-->

---
layout: statement
---

<div class="relative z-10 flex items-center justify-center h-full">

# <OrangeText>Can Java be improved?</OrangeText> Yes.

</div>

<!--
One yes, one question
-->

---
layout: statement
---

<div class="relative z-10 flex items-center justify-center h-full">

# <RedText>Are some existing features not the best?</RedText> Yes.

</div>

<!--
L:
-->

---
layout: statement
---

<div class="relative z-10 flex items-center justify-center h-full">

# <BlueText>Does it miss features other languages have?</BlueText> Yes.

</div>

<!--
L:
-->

---
layout: statement
---

<div class="relative z-10 flex items-center justify-center h-full flex-col">

# <OrangeText>Does it have a huge ecosystem?</OrangeText>
# <RedText>Does it run almost everywhere? </RedText>Also yes.

</div>

<!--
Johannes:

J: "This is straight from our article. Can Java be improved? Absolutely."
L: "Are some features not the best? Sure. Streams, modules, the old Date API..."
[click]
J: "But has it been around longer than its competitors? Is it a vibrant community? Is the runtime managed by more than one company? Does it run almost everywhere?"
L: "Also yes. To all of it."
J: "The honest answer isn't 'Java is the best.' It's 'Java is the most reliably good.'"
-->

---
layout: center
---

![](./img/java_wait.png)

<ImageAttribution>https://www.chartoasis.com/downloading-and-installing-java-cop3/</ImageAttribution>

<!--
Johannes
do you remember the installer from around 2009?
-->

---
layout: center
---

<div class="relative z-10">

<div class="big-statement">

Java 26 + 27 are <span class="text-emerald">boring</span> —<br/>except under the hood.

</div>

<v-click>


</v-click>

</div>

<!--
Johannes


this is a quote of Martin, one of J's colleagues
-->

---
layout: section
---

<div class="slide-content">

# Java 28 is certainly not boring

March 2027

</div>

<!--
Lutske
-->

---

# Java 28: What's coming

<div class="mt-2 text-sm">

| JEP | Feature | Status |
|-----|---------|--------|
| 544 | Ahead-of-Time Code Compilation | <Badge variant="gray">Incubator</Badge> |
| 401 | Value Objects (Project Valhalla) | <Badge variant="blue">Preview</Badge> |
| 468 | Derived Record Creation | <Badge variant="blue">Preview</Badge> |
| 539 | Strict Field Initialization in the JVM | <Badge variant="blue">Preview</Badge> |
| 540 | Simple JSON API | <Badge variant="gray">Incubator</Badge> |
| 541 | Deprecate macOS/x64 Port for Removal | <Badge variant="orange">Deprecation</Badge> |
| 542 | PEM Encodings of Cryptographic Objects | <Badge variant="green">Final</Badge> |
| 543 | Structured Concurrency | <Badge variant="green">Final</Badge> |
| 535 | Shenandoah GC: Generational Mode by Default | <Badge variant="green">Final</Badge> |
| 545 | ZGC: Faster Startup and Warmup | <Badge variant="green">Final</Badge> |
| 546 | ZGC: Adaptive Heap Sizing | <Badge variant="green">Final</Badge> |

</div>

<!--
Lutske
-->

---
layout: center
hide: t
---

<div class="slide-overlay" />
<div class="slide-content flex flex-col items-center justify-center h-full">

<div class="big-statement">Ahead-of-Time<br/>Code Compilation</div>

<div class="mt-6 text-xl text-gray-300 text-center max-w-2xl">

**JEP 544** <Badge variant="gray">Incubator</Badge> <Badge28/><br/>
Not just object caching. Not profiles.<br/><em>Compiled native machine code — stored before you run.</em>

</div>

</div>

<!--
J: "JEP 544 is the next layer in the AOT story. We already have JEP 516 — AOT object caching. JEP 544 goes further: it stores the actual JIT-compiled native code in the AOT cache during a training run. Production runs load finished machine code — no recompilation needed."
L: "So the warmup phase is gone?"
J: "That's the goal. Benchmarks show 65–80% faster startup. And by iteration 4, the AOT-cached app is already at steady-state while the JIT-only app is still warming up."
-->

---
layout: center
hide: true
---

<div class="slide-overlay" />
<div class="slide-content flex flex-col items-center justify-center h-full">

<div class="big-statement">Ahead-of-Time<br/>Code Compilation</div>

<div class="mt-6 text-xl text-gray-300 text-center max-w-2xl">

**JEP 544** <Badge variant="gray">Incubator</Badge> <Badge28/><br/>
Not just object caching. Not profiles.<br/><em>Compiled native machine code — stored before you run.</em>

</div>

</div>

<!--
J: "JEP 544 is the next layer in the AOT story. We already have JEP 516 — AOT object caching. JEP 544 goes further: it stores the actual JIT-compiled native code in the AOT cache during a training run. Production runs load finished machine code — no recompilation needed."
L: "So the warmup phase is gone?"
J: "That's the goal. Benchmarks show 65–80% faster startup. And by iteration 4, the AOT-cached app is already at steady-state while the JIT-only app is still warming up."
-->

---
layout: center
---

<img src="./img/wiki-valhalla.jpg" class="slide-bg opacity-100" style="object-position: center 30%;" />
<div class="slide-overlay" />
<div class="slide-content flex flex-col items-center justify-center h-full">

<div class="big-statement">Project Valhalla</div>

<div class="mt-6 text-xl text-gray-300 text-center max-w-2xl">

aka **_Value types_**

</div>

</div>

<div class="absolute bottom-4 right-6 text-xs text-slate-500 z-10">
  <em>Arrival at Valhalla</em> (Tjängvide image stone) · Berig · CC BY-SA 4.0
</div>

<!--
Johannes
-->

---

# Value Objects: What changes

<div class="grid grid-cols-2 gap-6 mt-3">
<div>

**`value` modifier — no identity**

```java
value class Point {
    final int x, y;
}

Point a = new Point(1, 2);
Point b = new Point(1, 2);
a == b   // true — fields match

// synchronized (a) { }  // error
```

</div>
<div>

**Why it matters — memory layout**

`LocalDate[]` of 1M entries today:
```
[ptr, ptr, ptr, …]
  ↓    ↓    ↓
{header+y+m+d} {header+y+m+d} …
```

With value objects:
```
[y,m,d, y,m,d, y,m,d, …]
```
No heap pointers. No GC pressure. Cache-friendly.

<div class="text-xs text-slate-500 mt-2">30 JDK classes become value classes: wrappers, Optional, java.time…</div>

</div>
</div>

<!--
Johannes
-->

---

# What Comes After Value Objects

<div class="mt-4 grid grid-cols-2 gap-8">
<div>

**JEP 402 — Enhanced Primitive Boxing** <span class="text-xs text-slate-500">Draft · JDK 29+</span>

Primitives as receivers — no more `Integer.MAX_VALUE`:

```java
int i = 42;
double d = i.doubleValue();
Supplier<String> s = i::toString;
int max = int.MAX_VALUE;
```

</div>
<div>

**Null-Restricted Types** <span class="text-xs text-slate-500">Draft · JDK 29–30?</span>

`!` suffix = statically non-nullable:

```java
Point! p = null;      // compile error
Point![] pts = new Point![3];
// pre-filled with zero instance
```

<div class="text-xs text-slate-500 mt-2">Two draft JEPs · active <code>bworld</code> prototype · syntax unstable</div>

</div>
</div>

<div class="mt-5 text-sm text-slate-400 text-center">

Also unblocks: **Vector API graduation** (stuck in incubator since JDK 16) · eventual **`List<int>`**

</div>

<!--
Johannes
-->

---

# Project Valhalla: 12 Years in the Making

<svg viewBox="-25 0 610 300" class="w-full" style="font-size: 1px;">
  <!-- Axis at y=145, spans x=15..545 -->
  <line x1="15" y1="145" x2="545" y2="145" stroke="#475569" stroke-width="1.3"/>

  <!-- 2014: Project started — ABOVE -->
  <circle cx="40" cy="145" r="6" fill="none" stroke="#64748b" stroke-width="0.8"/>
  <circle cx="40" cy="145" r="3" fill="#64748b"/>
  <line x1="40" y1="137" x2="40" y2="100" stroke="#64748b" stroke-width="0.8"/>
  <circle cx="40" cy="100" r="1.2" fill="#64748b"/>
  <text x="40" y="160" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#94a3b8">2014</text>
  <text x="40" y="92" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">Project started</text>
  <text x="40" y="79" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">Jul 2014</text>
  <line x1="0" y1="68" x2="80" y2="68" stroke="#64748b" stroke-width="1.5"/>
<g v-click>
  <!-- 2021: Vector API blocked — BELOW -->
  <circle cx="160" cy="145" r="6" fill="none" stroke="#64748b" stroke-width="0.8"/>
  <circle cx="160" cy="145" r="3" fill="#64748b"/>
  <line x1="160" y1="153" x2="160" y2="195" stroke="#64748b" stroke-width="0.8"/>
  <circle cx="160" cy="195" r="1.2" fill="#64748b"/>
  <text x="160" y="132" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#94a3b8">2021</text>
  <text x="160" y="208" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">Vector API incubator</text>
  <text x="160" y="220" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">waiting on Valhalla…</text>
  <line x1="112" y1="232" x2="208" y2="232" stroke="#64748b" stroke-width="1.5"/>
</g>
  <!-- JDK 26–27: Groundwork — ABOVE -->
<g v-click>
  <circle cx="280" cy="145" r="6" fill="none" stroke="#6366f1" stroke-width="0.8"/>
  <circle cx="280" cy="145" r="3" fill="#6366f1"/>
  <line x1="280" y1="137" x2="280" y2="100" stroke="#6366f1" stroke-width="0.8"/>
  <circle cx="280" cy="100" r="1.2" fill="#6366f1"/>
  <text x="280" y="160" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#a5b4fc">26–27</text>
  <text x="280" y="92" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">Primitives in patterns</text>
  <text x="280" y="79" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">5th preview · JVM groundwork</text>
  <line x1="218" y1="68" x2="342" y2="68" stroke="#6366f1" stroke-width="1.5"/>
</g>
  <!-- JDK 28: Value classes — BELOW -->
<g v-click>
  <circle cx="390" cy="145" r="6" fill="none" stroke="#a5b4fc" stroke-width="0.8"/>
  <circle cx="390" cy="145" r="3" fill="#a5b4fc"/>
  <line x1="390" y1="153" x2="390" y2="195" stroke="#a5b4fc" stroke-width="0.8"/>
  <circle cx="390" cy="195" r="1.2" fill="#a5b4fc"/>
  <text x="390" y="132" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#c7d2fe">JDK 28</text>
  <text x="390" y="208" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0">JEP 401 + 539 — first preview</text>
  <text x="390" y="220" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8">~208K lines · Mar 2027</text>
  <line x1="338" y1="232" x2="442" y2="232" stroke="#a5b4fc" stroke-width="1.5"/>
</g>
  <!-- JDK 29+: Null-restricted types — ABOVE (dashed = draft) -->
<g v-click>
  <circle cx="510" cy="145" r="6" fill="none" stroke="#7c3aed" stroke-width="0.8" stroke-dasharray="3,2"/>
  <circle cx="510" cy="145" r="3" fill="#7c3aed" opacity="0.6"/>
  <line x1="510" y1="137" x2="510" y2="100" stroke="#7c3aed" stroke-width="0.8" stroke-dasharray="3,2"/>
  <circle cx="510" cy="100" r="1.2" fill="#7c3aed" opacity="0.6"/>
  <text x="510" y="160" text-anchor="middle" style="font-size: 14px; font-weight: bold;" fill="#a78bfa" opacity="0.8">29+?</text>
  <text x="510" y="92" text-anchor="middle" style="font-size: 10px;" fill="#e2e8f0" opacity="0.75">Point! — null-restricted</text>
  <text x="510" y="79" text-anchor="middle" style="font-size: 9px;" fill="#94a3b8" opacity="0.75">bworld branch · 2 draft JEPs</text>
  <line x1="458" y1="68" x2="562" y2="68" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="4,2"/>
</g>
</svg>

<!--
Lutske
-->

---
layout: center
---

<div class="slide-overlay" />
<div class="slide-content flex flex-col items-center justify-center h-full">

<div class="big-statement">

The <BlueText>boring</BlueText> years<br/>paid for this.

</div>

</div>

<!--
Lutske
-->

---
layout: section
---

<div class="slide-content">

# Closing

Boring and brilliant

</div>

<!--
Johannes
-->

---

# Like the awesome voice talent

<div class="grid grid-cols-8 gap-2 mt-4 text-center text-xs">

<!-- Original speakers with photos -->
<div>
  <img src="https://confoo.ca/images/speakers/2026/mikael-francoeur_l.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Mikaël Francoeur</div>
</div>

<div>
  <img src="https://www.kodewerk.com/about/head_shot.png"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Kirk Pepperdine</div>
</div>

<div>
  <img src="https://avatars.githubusercontent.com/u/1297282?v=4"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Pasha Finkelshteyn</div>
</div>

<div>
  <img src="https://sessionize.com/image/1817-400o400o2-25-a949-43ac-971f-cec885fa060b.c84e95d2-1366-4eda-b6f0-0482e38b3cf1.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Sandra Parsick</div>
</div>

<div>
  <img src="https://sessionize.com/image/93e3-400o400o2-8a-56cf-40ec-bc39-ca5d9fb59b27.74a2c239-83f3-4fd7-a70b-3b18c40df894.png"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Ivar Grimstad</div>
</div>

<div>
  <img src="https://sessionize.com/image/f0ab-400o400o2-9gcFoW7JGxVoMKM2pyAMb5.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">François Martin</div>
</div>

<div>
  <img src="https://2020.hroug.hr/var/ezdemo_site/storage/images/hroug-2020/predavaci/jasminfluri/468288-2-eng-EU/Fluri-Jasmin_lecturerportrait.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Jasmin Fluri</div>
</div>

<!-- New contributors with photos -->
<div>
  <img src="https://sessionize.com/image/c17c-400o400o2-RzyLob7uSE6Nmun9e4Vnxn.png"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Anders Norås</div>
</div>

<div>
  <img src="https://sessionize.com/image/7a22-400o400o2-EX3sJi17SvAbLkE1qQkHNz.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Daniel Raniz Raneland</div>
</div>

<div>
  <img src="https://s3.eu-west-1.amazonaws.com/redsys-prod/authors/6faf182b89427e7064e5b4b9/images/avatarSquareSmall_xxx_1765876608463luciacondemoreno28129.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Lucía Conde-Moreno</div>
</div>

<div>
  <img src="https://files.gotocon.com/uploads/portraits/570/square_medium/paulien_van%20alst_1548154731.jpeg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Pauline Van Alst</div>
</div>

<div>
  <img src="https://www.baeldung.com/wp-content/uploads/2024/08/Ronald-Dehuysser.png"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Ronald Dehuysser</div>
</div>

<div>
  <img src="https://sessionize.com/image/9d71-400o400o2-BtS74DLX6NUMv3g9z9LXEs.png"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Adele Carpenter</div>
</div>

<div>
  <img src="https://media.licdn.com/dms/image/v2/D4D03AQGmKvJc2L0Jww/profile-displayphoto-scale_200_200/B4DZgOKHACHwAo-/0/1752584188746?e=2147483647&v=beta&t=EQjDOywGjSwd1C7JkbNRygG8CgzCdYWul0iSZg99uHU"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Dimitris Doutsiopoulos</div>
</div>

<div>
  <img src="https://sessionize.com/image/f0ab-400o400o2-9gcFoW7JGxVoMKM2pyAMb5.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">François Martin</div>
</div>

<div>
  <img src="https://devoxxian-image-thumbnails.s3-eu-west-1.amazonaws.com/profile-c4c10d21-e508-4d32-839a-5a92128ce54c.png"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Johan Hutting</div>
</div>

<div>
  <img src="https://sessionize.com/image/a1a5-400o400o2-5d453734-1a61-4d8d-b234-55fdf95d1202.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Josh Long</div>
</div>

<div>
  <img src="https://sessionize.com/image/0df4-400o400o2-EupDehSbyCtxrWHgadQRhp.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Ko Turk</div>
</div>

<div>
  <img src="https://sessionize.com/image/f289-400o400o2-RrURZVaRSiydVXHyA4yjBv.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Patrick Baumgartner</div>
</div>

<div>
  <img src="https://sessionize.com/image/51b7-400o400o2-BfjoyFEbryFsEXTK36uSu4.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Stephan Janssen</div>
</div>

<div>
  <img src="https://sessionize.com/image/bf90-400o400o2-GtCdR9gUG6mnWf76NhGJi8.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Susanne Pieterse</div>
</div>

<div>
  <img src="https://sessionize.com/image/8b71-400o400o2-8e0e2031-a42f-42ac-a720-e348d3be9d09.jpg"
       class="w-20 h-20 rounded-full mx-auto object-cover" />
  <div class="mt-0.5 font-medium text-xs">Victor Rentea</div>
</div>

</div>

<!--
Johannes

These people contributed their boringness
-->

---

<div class="relative z-10 h-full">

# Key takeaways

<div class="flex flex-col justify-center h-full gap-4 px-6" style="margin-top: -2cm">

<div class="text-2xl">

🚀 **Upgrade for free performance.**<br/>

</div>



<div class="text-2xl">

📚 **New features are for libraries. You benefit anyway.**


</div>
<div class="text-2xl">

🧱 **Boring process. Brilliant results.**<br/>
</div>


</div>

</div>

<!--
Lutske
-->

---
layout: center
---


<div class="relative z-10">

<div class="big-statement">

<span class="text-emerald">Evolution </span>over <BlueText>revolution</BlueText>

</div>

<div class="text-xl mt-8">

For another 30 years of *boring* Java.

</div>

</div>

<!--
L: "Evolution over revolution kept Java alive for 30 years. Careful language design and runtime work should keep it relevant for much longer. No rewrites, no breaking changes — just steady, boring, predictable progress."

-->

---
layout: center
---

<div class="relative z-10">

# Thank you! 🎉

<div class="grid grid-cols-2 gap-12 mt-12">

<div class="text-center">

### Lutske van der Meer

<!-- add socials here -->
github.com/Lutske

</div>

<div class="text-center">

### Johannes Bechberger

<!-- add socials here -->
mostlynerdless.de

</div>

</div>

<div class="grid grid-cols-1">

<div class="text-gray-400 ml-50 mt-12 text-lg" style="text-align: center">

![[https://github.com/parttimenerd/java26-27-are-boring](https://github.com/parttimenerd/java26-27-are-boring)](./img/repo_qr.png)

</div>
</div>

</div>

<!--
Lutske
-->
