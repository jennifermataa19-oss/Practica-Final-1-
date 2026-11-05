# Investigación: Qué es la Teoría de la Computación
**Unidad Temática I - Fundamentos Lógico-Matemáticos**  
*Documento de Investigación Estudiantil*

---

## 1. Introducción
En este documento vamos a abarcar los fundamentos de la Teoría de la Computación, pedidos en la práctica. Se analizan de forma profunda las definiciones principales de la disciplina, sus orígenes históricos vinculados al programa de Hilbert, las paradojas lógicas y el *Entscheidungsproblem*. Asimismo, se desglosan sus tres ramas fundamentales (computabilidad, complejidad y autómatas), la importancia de la Tesis de Church-Turing, y los conceptos formales de lenguajes, alfabetos y operaciones sobre cadenas. Finalmente, se explica la jerarquía de Chomsky y se formaliza la definición de autómatas finitos, destacando su equivalencia y aplicaciones en el mundo real, buscando establecer una comprensión exhaustiva de las bases de nuestra disciplina.

---

## 2. ¿Qué es la Teoría de la Computación y qué preguntas se plantea?
La Teoría de la Computación es el pilar teórico de las ciencias de la computación y la ingeniería en sistemas. Trata de descubrir qué problemas pueden ser resueltos mediante algoritmos y, de ser así, con qué nivel de eficiencia en cuanto a tiempo y memoria.

Existen múltiples formas de definirla dependiendo del enfoque que le demos:
* Según **Hopcroft et al.**, se define como *"el estudio de los fundamentos lógicos y matemáticos de la computación, centrada en los límites de lo que las máquinas abstractas pueden y no pueden hacer"* [[4](#ref-4)].
* Por otro lado, **Kelley** la define en su obra señalando que es *"la rama de la informática que trata de qué puede ser computado y qué recursos son necesarios para hacerlo, estableciendo modelos matemáticos de las computadoras"* [[6](#ref-6)].
* Además, el **programa sintético del IPN** la concibe como una asignatura crítica para fundamentar el diseño de compiladores y el análisis de algoritmos [[5](#ref-5)].

Si comparamos ambas definiciones formales, la de Hopcroft se enfoca en la naturaleza abstracta y los límites absolutos del procesamiento [[4](#ref-4)], mientras que la de Kelley incluye una perspectiva muy orientada a los recursos y a los modelos matemáticos de máquinas específicas [[6](#ref-6)]. Ambas concuerdan en que la disciplina busca responder a preguntas trascendentales:
* ¿Cuáles son los límites fundamentales del procesamiento de información?
* ¿Existe algún algoritmo para resolver determinado problema matemático?
* ¿Qué hace que algunos problemas sean intratables computacionalmente, incluso con el hardware más avanzado?

---

## 3. Sus orígenes: el programa de Hilbert y las paradojas
La Teoría de la Computación no nació cuando se inventaron las computadoras de transistores; sus raíces son puramente matemáticas y surgieron a principios del siglo XX con el **programa de Hilbert**. David Hilbert propuso un proyecto ambicioso: fundamentar todas las matemáticas basándose en un conjunto finito y estricto de axiomas. Él quería demostrar que este sistema matemático era **consistente** (sin contradicciones) y **completo** (que toda afirmación verdadera podría ser demostrada a partir de los axiomas).

Dentro de este enorme proyecto surgió el llamado ***Entscheidungsproblem*** o "problema de decisión". Hilbert preguntaba al mundo si existía un procedimiento mecánico y general (un algoritmo) que pudiera decidir automáticamente si una afirmación matemática dada era verdadera o falsa basándose en esos axiomas.

Sin embargo, las paradojas de la lógica matemática arruinaron esta utopía:
1. **La Paradoja de Russell:** Demostró que la teoría de conjuntos ingenua (propuesta por Cantor y Frege) tenía fallas estructurales graves. Russell propuso imaginar el conjunto de todos los conjuntos que no se contienen a sí mismos (similar a la paradoja del barbero).
2. **Teoremas de Incompletitud de Kurt Gödel (1931):** Gödel demostró matemáticamente que ningún sistema axiomático lo suficientemente complejo puede ser a la vez consistente y completo. Siempre habrá verdades matemáticas que no se pueden demostrar dentro del sistema.
3. **Alan Turing y Alonzo Church:** De forma independiente, asestaron el golpe final demostrando que el *Entscheidungsproblem* no tenía solución. Turing ideó su famosa "máquina de Turing" y demostró que no existe un algoritmo universal que pueda decidir la verdad o falsedad de cualquier enunciado lógico. Con este "no" matemático, nació formalmente la ciencia de la computación [[3](#ref-3)].

---

## 4. Las Tres Ramas de la Teoría
Para estructurar su estudio, la disciplina se dividió en tres ramas principales [[5](#ref-5)]:

### 4.1 Teoría de Autómatas y Lenguajes Formales
Responde a la pregunta: *¿Cómo modelamos matemáticamente el cálculo y el procesamiento de cadenas de texto?*  
Esta rama se encarga de definir máquinas abstractas (autómatas) y reglas de generación de sintaxis (gramáticas). Aquí estudiamos desde máquinas simples con memoria finita (como los autómatas finitos, que a nivel de hardware podríamos implementar en un dispositivo lógico programable como un GAL22V10 usando lenguajes descriptivos como VHDL) hasta máquinas complejas [[2](#ref-2)].

### 4.2 Teoría de la Computabilidad
Responde a la pregunta: *¿Qué problemas pueden ser resueltos por una computadora y cuáles son inherentemente irresolubles?*  
Clasifica los problemas en decidibles (computables) e indecidibles. Turing demostró, por ejemplo, el famoso **Problema de la Parada (Halting Problem)**: es imposible escribir un programa en C, C++, Python o cualquier lenguaje que analice a otro programa y determine siempre con certeza si ese segundo programa terminará de ejecutarse o se quedará en un bucle infinito.

### 4.3 Teoría de la Complejidad Computacional
Responde a la pregunta: *¿Qué hace que algunos problemas sean computacionalmente fáciles y otros prácticamente imposibles?*  
Incluso si un problema es computable, podría tomar millones de años resolverlo. Aquí se estudian los recursos (tiempo de procesamiento y memoria RAM o espacio) que requiere un algoritmo, clasificando los problemas en clases de complejidad como **P** (polinomial, resoluble rápidamente) y **NP** (no determinista polinomial, cuyas soluciones son rápidas de verificar pero, presuntamente, lentas de encontrar).

---

## 5. La Tesis de Church-Turing
Afirma que cualquier función que sea efectivamente calculable por un ser humano siguiendo un algoritmo (un conjunto de instrucciones paso a paso), puede ser calculada por una **Máquina de Turing**.

En la década de 1930, Alonzo Church propuso un sistema formal llamado el Cálculo Lambda ($\lambda$-cálculo) para definir funciones computables. Casi al mismo tiempo, Alan Turing propuso su famosa Máquina de Turing [[3](#ref-3)].

Poco después, se demostró matemáticamente que el modelo de Turing, el cálculo Lambda de Church y las funciones recursivas parciales de Gödel-Herbrand eran modelos completamente equivalentes. A pesar de tener arquitecturas lógicas totalmente distintas, los tres pueden calcular exactamente el mismo conjunto de funciones. Todo lenguaje de programación moderno (C++, PHP, Python) es Turing completo.

### ¿Por qué se denomina "tesis" y no "teorema"?
Un teorema matemático relaciona dos conceptos formales mediante una demostración lógica. Sin embargo, la Tesis de Church-Turing relaciona un concepto matemático rígidamente formalizado (la Máquina de Turing) con un concepto puramente intuitivo y humano (el "cálculo efectivo" o algoritmo). Al no poder formalizarse matemáticamente la "intuición", la afirmación no puede ser demostrada con un teorema formal. Sin embargo, ha sido validada por casi un siglo de investigación sin que se haya encontrado ningún contraejemplo.

---

## 6. Conceptos Formales: Alfabeto, Cadena y Lenguaje
Para poder hacer demostraciones rigurosas, necesitamos abstraer los datos a sus componentes más básicos utilizando teoría de conjuntos [[2](#ref-2), [4](#ref-4)]. El aprendizaje de estos conceptos formales requiere una asimilación gradual y significativa de la lógica subyacente [[1](#ref-1)].

* **Alfabeto ($\Sigma$):** Es un conjunto finito, no vacío, de símbolos indivisibles. Por ejemplo, el alfabeto binario $\Sigma = \{0, 1\}$, o el alfabeto del ADN $\Sigma = \{A, C, G, T\}$.
* **Cadena ($w$):** También llamada "palabra", es una secuencia finita de símbolos elegidos de un alfabeto. Su longitud, denotada como $\vert{}w\vert{}$, es el número de símbolos que la componen. Por ejemplo, si $w = 1011$, entonces $\vert{}w\vert{} = 4$. Existe una cadena especial de longitud cero, denotada como $\lambda$ o $\epsilon$ (cadena vacía).
* **Lenguaje ($L$):** Es un conjunto, finito o infinito, de cadenas formadas a partir de un alfabeto específico. Formalmente, es cualquier subconjunto del conjunto de todas las cadenas posibles, es decir, $L \subseteq \Sigma^*$. Un lenguaje de programación entero, como SQL, es un lenguaje formal complejo, y el compilador/intérprete decide si una cadena de texto pertenece o no a ese lenguaje.

### 6.1 Las operaciones formales
Sobre las cadenas y los lenguajes podemos aplicar varias operaciones matemáticas:
* **Concatenación de cadenas:** Unir dos cadenas una tras otra. Si $x = 01$ y $y = 11$, entonces $xy = 0111$.
* **Concatenación de lenguajes:** $L_1 L_2 = \{xy \mid x \in L_1, y \in L_2\}$.
* **Potencia ($L^n$):** Consiste en concatenar un lenguaje consigo mismo $n$ veces ($L^2 = LL$).
* **Reflexión ($L^R$):** El conjunto de todas las cadenas del lenguaje leídas al revés. Si $0100 \in L$, entonces $0010 \in L^R$.
* **Unión ($L_1 \cup L_2$):** Conjunto de cadenas que pertenecen a $L_1$, a $L_2$, o a ambos.
* **Intersección ($L_1 \cap L_2$):** Conjunto de cadenas presentes simultáneamente tanto en $L_1$ como en $L_2$.
* **Diferencia ($L_1 - L_2$):** Conjunto de cadenas que pertenecen a $L_1$ pero definitivamente no están en $L_2$.
* **Cerradura de Kleene ($\Sigma^*$):** Es el conjunto infinito de todas las cadenas posibles de cualquier longitud que se puedan formar con los símbolos de $\Sigma$, incluyendo forzosamente la cadena vacía $\lambda$.
* **Cerradura Positiva ($\Sigma^+$):** Es idéntica a la cerradura de Kleene, pero sin garantizar la inclusión de la cadena vacía. Representa todas las cadenas de longitud 1 o mayor.

#### Preguntas Frecuentes sobre Operaciones
* **¿Por qué $\Sigma^0 = \{\lambda\}$?:** La potencia cero de un conjunto de símbolos ($L^0$ o $\Sigma^0$) significa extraer todas las combinaciones posibles que generen cadenas de longitud exactamente cero. La única secuencia lógica y matemáticamente posible de longitud cero es la cadena vacía ($\lambda$). Por tanto, el conjunto resultante contiene a este único elemento neutro.
* **¿Qué distingue a $\Sigma^*$ de $\Sigma^+$?:** La única distinción estructural es la cadena vacía. Matemáticamente se expresa como $\Sigma^* = \Sigma^+ \cup \{\lambda\}$. La cerradura de Kleene ($*$) modela situaciones donde "no recibir ninguna entrada" es válido, mientras que la cerradura positiva ($+$) exige al menos un símbolo de entrada.

---

## 7. La Jerarquía de Chomsky
En la década de 1950, Noam Chomsky propuso una clasificación de los lenguajes formales basada en la estructura de sus reglas de producción (gramáticas). Esta jerarquía es el núcleo teórico para el diseño de analizadores léxicos y sintácticos en compiladores modernos [[6](#ref-6)].

| Tipo | Gramática | Máquina que lo reconoce |
| :---: | :--- | :--- |
| **0** | Irrestricta (Recursivamente enumerable) | Máquina de Turing (MT) |
| **1** | Sensible al contexto | Autómata Linealmente Acotado (LBA) |
| **2** | Libre de contexto | Autómata de Pila (Push-down Automaton) |
| **3** | Regular | Autómata Finito (AFD / AFN) |

* **Tipo 3 (Regular):** Las reglas de producción solo permiten un símbolo no terminal a la derecha o a la izquierda, ideal para modelar validaciones simples de texto.
* **Tipo 2 (Libre de Contexto):** Un símbolo no terminal produce cualquier cadena de terminales y no terminales. Es la base de lenguajes como C o Python; el autómata de pila usa su memoria LIFO para asegurar que paréntesis y llaves se abran y cierren correctamente.
* **Tipo 1 (Sensible al Contexto):** Las reglas dependen del entorno (contexto) del símbolo no terminal.
* **Tipo 0 (Irrestricta):** No hay reglas sobre la longitud o composición de las producciones. Modela cualquier cosa computable.

---

## 8. Autómatas Finitos y Expresiones Regulares
Centrándonos en el Tipo 3 de la jerarquía, los lenguajes regulares se procesan con **Autómatas Finitos**. Son máquinas abstractas con una memoria limitada a recordar su estado actual. Son análogos a nivel teórico de los circuitos lógicos secuenciales que combinan compuertas y flip-flops, avanzando de un estado a otro con cada pulso de reloj [[6](#ref-6)].

### Autómata Finito Determinista (AFD)
Es el modelo más estricto y predecible. Se define formalmente como una quintupla matemática $M = (Q, \Sigma, \delta, q_0, F)$ donde:
* $Q$ es un conjunto finito de estados posibles.
* $\Sigma$ es el alfabeto finito de entrada.
* $\delta: Q \times \Sigma \rightarrow Q$ es la función de transición (dado un estado y un símbolo, indica un único estado siguiente).
* $q_0 \in Q$ es el estado inicial.
* $F \subseteq Q$ es el conjunto de estados finales o de aceptación.

### Autómata Finito No Determinista (AFN)
Comparte la misma quintupla $(Q, \Sigma, \delta, q_0, F)$, pero su función de transición mapea hacia el conjunto potencia de los estados: $\delta: Q \times \Sigma \rightarrow \mathcal{P}(Q)$. Desde un estado y leyendo un símbolo, la máquina puede ir a múltiples estados simultáneamente.

A pesar de que el AFN puede "adivinar" rutas paralelas, **ambos modelos son completamente equivalentes**. El algoritmo de *Construcción de subconjuntos* permite convertir cualquier AFN en un AFD, simulando los estados paralelos como un único macro-estado. Si el AFN tiene $n$ estados, el AFD resultante podría llegar a tener hasta $2^n$ estados.

### 8.1 Aplicaciones Reales de las Expresiones Regulares
Las expresiones regulares son la representación algebraica de los autómatas finitos. Tienen aplicaciones cotidianas en ingeniería de software:
1. **Análisis Léxico en Compiladores e Intérpretes:** Agrupar caracteres en *tokens* (palabras clave como `while`, operadores como `++`, identificadores o números) mediante un AFD basado en expresiones regulares.
2. **Validación de Integridad en Formularios y Bases de Datos:** Asegurar formatos válidos en bases de datos relacionales (PostgreSQL, MySQL) para correos, números telefónicos o prevenir inyecciones SQL.
3. **Búsqueda y Reemplazo de Patrones Complejos en Editores:** Herramientas como `grep` o entornos de desarrollo (IDEs) utilizan expresiones regulares para manipular o actualizar código en cientos de archivos simultáneamente.

---

## 9. Conclusión
A lo largo de este documento de investigación, hemos recorrido las bases fundamentales de la Teoría de la Computación. Empezamos analizando las crisis lógicas generadas por Hilbert, Russell y Gödel que dieron paso a las definiciones fundacionales de Turing. Posteriormente, desglosamos la formalidad de los alfabetos y los lenguajes, para finalmente conectar esta teoría altamente abstracta de autómatas y expresiones regulares con las herramientas de software tangibles que los ingenieros en sistemas emplean en la actualidad para compilar lenguajes, proteger bases de datos y manipular grandes flujos de información estructurada.

---

## Referencias

<a id="ref-1"></a>[1] F. Díaz Barriga y G. Hernández Rojas, *Estrategias docentes para un aprendizaje significativo*. México: McGraw Hill, 2016. ISBN: 978-607-15-0293-3.

<a id="ref-2"></a>[2] H. Díaz, *Lenguajes y autómatas*. Universidad Autónoma Metropolitana, 2020. ISBN: 978-607-28-1819-4.

<a id="ref-3"></a>[3] A. Hodges, "Alan Turing home page," Recuperado el 26 de agosto de 2024. [Online]. Disponible en: https://www.turing.org.uk/index.html

<a id="ref-4"></a>[4] J. E. Hopcroft, R. Motwani y J. D. Ullman, *TEORÍA DE AUTÓMATAS, LENGUAJES Y COMPUTACIÓN*, 3rd ed. Addison-Wesley, 2007. ISBN: 8478290885.

<a id="ref-5"></a>[5] Instituto Politécnico Nacional, *Programa sintético: Teoría de la Computación*. Secretaría Académica, Dirección de Educación Superior, Escuela Superior de Cómputo (ESCOM), UPIIZ, 2020.

<a id="ref-6"></a>[6] D. Kelley, *Teoría de autómatas y lenguajes formales*. Prentice Hall, 2001. ISBN: 9780135187050.