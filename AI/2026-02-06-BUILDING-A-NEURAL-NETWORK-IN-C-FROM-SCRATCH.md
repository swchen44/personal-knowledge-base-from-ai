---
title: "從零開始用 C 語言打造神經網路（逐步教學）"
date: 2026-02-06
category: AI
tags:
  - "#ai/neural-network"
  - "#ai/ml-fundamentals"
  - "#code/c"
  - "#ai/education"
  - "#ai/from-scratch"
source: "https://x.com/TheVixhal/status/2019831123682181418"
source_type: article
author: "vixhaℓ (@TheVixhal)"
status: notes
links:
  - "[[2026-04-12-HARNESS-ENGINEERING-HUNGYI-LEE-NTU-LLM-GUIDANCE]]"
  - "[[2025-10-16-DESIGN-YOUR-SOCRATIC-AI-MENTOR-FRAMEWORK]]"
  - "[[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]]"
---

## 摘要（Summary）

本文是一篇逐步（step-by-step）教學，示範如何**完全不靠任何函式庫或框架，純用 C 語言從零打造一個神經網路（Neural Network）**。作者 vixhaℓ（物理與 AI/ML 雙主修）的核心主張是：**先理解「為什麼（why）」再談「怎麼做（how）」**——每個概念都先解釋清楚才寫成程式碼。

範例任務是用「房間數、坪數、距市場距離」三個特徵預測**房價（House Price Prediction）**，網路結構為 `3 → 4 → 1`（3 輸入、4 隱藏神經元、1 輸出）。文章完整走過：單一神經元的運算、ReLU 激活函數、前向傳播（Forward Propagation）、損失函數（MSE）、反向傳播（Backward Propagation）與梯度下降（Gradient Descent），最後給出可直接 `gcc` 編譯執行的完整 C 程式。

> [!info] 本筆記的加值
> 除翻譯原文外，本筆記額外用 **ccq（clangd 驅動的 C/C++ 程式碼智慧工具）** 解析完整原始碼，繪出真實的**函式呼叫圖（call graph）**與資料流，並附上**實際編譯執行的輸出**——揭露原文沒提到的一個重要事實：以原文的超參數（learning rate 與 epochs）訓練，模型其實學得很差。

## 關鍵洞察（Key Insights）

- **「先 why 再 how」的教學法**——本文每段都先用生活化比喻（房仲、霧中下山）建立直覺，再導入數學與程式碼，與 [[2025-10-16-DESIGN-YOUR-SOCRATIC-AI-MENTOR-FRAMEWORK]] 的蘇格拉底式「理解優先」精神一致。
- **神經網路 = 一隊專家**——每個神經元（neuron）是一位專家，每層（layer）是一個團隊，最終由輸出層整合所有意見。這是理解隱藏層職責的直覺模型。
- **為什麼需要激活函數**——若沒有非線性的激活函數（如 ReLU），疊再多層也只是另一個線性函數，學不到複雜的非線性模式。
- **正規化（Normalization）是隱形關鍵**——坪數（1500）量級遠大於房間數（3），不正規化會讓大數值特徵主宰一切、學習緩慢不穩。
- **反向傳播 = 霧中下山**——梯度（gradient）告訴你每個權重「往哪個方向走能降低誤差」，學習率（learning rate）控制步伐大小。
- **「最深層的理解」**——作者強調看懂這份程式碼後，你是從**實際的數學與程式碼**理解神經網路，呼應 [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]]「可外包思考，無法外包理解」。

---

## 詳細內容（Details）

### Part 1：理解基礎（Understanding the Basics）

#### 1.1 我們在解決什麼問題？

想像你是房仲。客戶問：「這間房子該值多少？」你會看：房間數（3 房）、坪數（1,500 平方英尺）、地點（離市場 2 公里）。你的大腦看過上百間房子、學到了模式，於是判斷「類似的房子大約賣 $300,000」。**這正是我們要教電腦做的事——從資料中學習模式。**

#### 1.2 為什麼不能只用一條簡單公式？

你可能會想，直接寫一條公式就好：

```markdown
Price = (rooms × 50000) + (sqft × 100) + (market_distance × -20000)
```

問題是房地產沒這麼單純：

- 5 房但地點差的房子，未必勝過 3 房但地點好的房子。
- 坪數對大房子的影響比對小房子更大。
- 特徵之間以複雜方式互相影響（interact）。

我們需要一個能學習這些**非線性模式（non-linear patterns）**的東西。

#### 1.3 登場：神經網路

把神經網路想成**一隊專家（a team of specialists）**：

```
Specialist 1: I focus on luxury indicators - rooms + size combined
Specialist 2: I focus on location quality
Specialist 3: I look for budget-friendly markers
Specialist 4: I detect suburban vs urban patterns

Final Appraiser: Combines all opinions → Price estimate
```

每個「專家」就是一個神經元（neuron），整個「團隊」就是一層神經元（a layer of neurons）。

#### 1.4 我們的網路架構

```markdown
INPUT LAYER     HIDDEN LAYER      OUTPUT LAYER
(3 features)    (4 neurons)       (1 prediction)

[rooms]    \    [Neuron 1]
[area]     →→→→ [Neuron 2]  →→→→  [price]
[distance] /    [Neuron 3]
                [Neuron 4]
```

**為什麼是 4 個隱藏神經元？** 太少：學不到複雜模式；太多：可能「死記（memorize）」而非學習模式；對這個簡單資料集，4 是不錯的折衷。

### Part 2：數學（The Mathematics）

> [!note] 關鍵術語（Key Term）：神經元的兩步運算
> 一個神經元做兩件簡單的事：① **加權總和（Weighted Sum）**——把各輸入乘上權重再加偏差（bias）；② **激活函數（Activation Function）**——加入非線性。

#### 2.1 一個神經元做什麼？

**步驟一：加權總和（線性組合）**

```markdown
z = (w₁ × input₁) + (w₂ × input₂) + (w₃ × input₃) + bias
```

把權重（weights）想成「我有多在乎這個輸入？」。範例：

```markdown
weights = [w₁ = 0.5, w₂ = 0.3, w₃ = -0.2]   ← 房間數與坪數重要，距離略為負向
inputs  = [rooms = 3, area = 1500, market_distance = 2]
bias = 0.1

z = (0.5 × 3) + (0.3 × 1500) + (-0.2 × 2) + 0.1
z = 1.5 + 450 + (-0.4) + 0.1
z = 451.2
```

**步驟二：激活函數**——加入非線性。若沒有它，疊很多神經元只會變成另一個線性函數。

```markdown
output = activation(z)
```

#### 2.2 激活函數：ReLU

我們用 **ReLU（Rectified Linear Unit，修正線性單元）**：

```markdown
ReLU(x) = x if x > 0, else 0
```

白話：**保留正數，把負數歸零。**

```markdown
Input:  -5  -2   0   2   5
Output:  0   0   0   2   5
         ↑   ↑   ↑   ↑   ↑
       killed killed kept kept kept
```

**為什麼用 ReLU？** 計算簡單（就是 `max(0, x)`）、幫助網路更快學習、緩解「梯度消失（vanishing gradient）」問題、引入非線性讓網路能學曲線。

**為什麼輸出層不用 ReLU？** 我們的輸出是房價，可以是任意數值；ReLU 會強制為正，而且我們希望最後是直接的線性映射（linear mapping）。

#### 2.3 前向傳播：做一次預測

以一間 3 房、1500 sqft、離市場 2 km 的房子，用一組隨機初始權重，逐神經元計算（原文完整數值推導）：

```markdown
Input → Hidden weights:
Neuron1: [0.2, 0.1, -0.3]  bias: 0.1
Neuron2: [-0.1, 0.2, 0.1]  bias: -0.05
Neuron3: [0.15, -0.1, 0.2] bias: 0.2
Neuron4: [0.3, 0.05, -0.1] bias: -0.15

Hidden → Output weights:
Output: [0.5, 0.3, -0.2, 0.1] bias: 0.05
```

```markdown
Neuron 1: z₁ = (0.2×3)+(0.1×1500)+(-0.3×2)+0.1 = 150.1   → a₁ = ReLU(150.1) = 150.1 ✓
Neuron 2: z₂ = (-0.1×3)+(0.2×1500)+(0.1×2)-0.05 = 299.85 → a₂ = ReLU(299.85) = 299.85 ✓
Neuron 3: z₃ = (0.15×3)+(-0.1×1500)+(0.2×2)+0.2 = -148.95 → a₃ = ReLU(-148.95) = 0 ✗ (killed!)
Neuron 4: z₄ = (0.3×3)+(0.05×1500)+(-0.1×2)-0.15 = 75.55  → a₄ = ReLU(75.55) = 75.55 ✓

Hidden layer output: [150.1, 299.85, 0, 75.55]

z_out = (0.5×150.1)+(0.3×299.85)+(-0.2×0)+(0.1×75.55)+0.05 = 172.61
output = 172.61   (輸出層無激活)

Prediction: $172,610
```

**問題：** 若實際房價是 $300,000，這個預測差很大！因為權重是隨機的，所以預測很糟——這就是「學習」要登場的地方。

#### 2.4 問題：尺度（scale）不一致

注意到坪數（1500）遠大於房間數（3）嗎？這會讓學習困難、某些特徵被忽略、學習緩慢不穩。**解法：把所有輸入正規化到同一尺度 [0, 1]。**

```markdown
normalized = (value - min) / (max - min)
```

```markdown
Rooms:    min=2, max=6     →  3 rooms  → (3-2)/(6-2) = 0.25
Area:     min=900, max=3000 → 1500 sqft → (1500-900)/(3000-900) = 0.286
Distance: min=0.8, max=4    → 2.0 km   → (2.0-0.8)/(4-0.8) = 0.375
```

#### 2.5 衡量錯誤：損失函數（Loss Function）

用**均方誤差（Mean Squared Error, MSE）**：

```markdown
Loss = (predicted - actual)²
```

**為什麼平方？** 讓所有誤差變正（好比較）、大誤差被懲罰得更重、數學上對梯度運算很順。

#### 2.6 學習：反向傳播

> [!tip] 直覺——霧中下山（The Hill Analogy）
> 你在霧中的山上看不見山腳，但想下去。怎麼做？**感覺哪邊往下、就往那個方向踏一步。** 在神經網路裡：「山」是誤差表面、你的位置是當前權重、「往下」是降低誤差的方向、「一步」是更新權重。**梯度（gradient）告訴你每個權重的下坡方向。**

**更新規則（Update Rule）：**

```markdown
new_weight = old_weight - (learning_rate × gradient)
```

學習率太大會「衝過頭」來回震盪；太小則學得超慢；剛好才能穩定地往下走。

#### 2.7 計算梯度（鏈鎖法則 Chain Rule）

對輸出神經元：

```markdown
∂Loss/∂weight = ∂Loss/∂output × ∂output/∂weight

對 MSE + 線性輸出：
∂Loss/∂output = 2 × (predicted - actual)
∂output/∂weight = hidden_activation

所以：gradient = 2 × (predicted - actual) × hidden_activation
```

通常簡化為直接用 `(predicted - actual)`（省略係數 2）。對隱藏層，用鏈鎖法則把誤差往回傳：

```markdown
hidden_error = output_error × weight × ReLU_derivative
```

ReLU 的導數：神經元活躍（z > 0）時為 1，被歸零（z ≤ 0）時為 0。**為什麼？** 若一個神經元被 ReLU 歸零，它沒有貢獻到輸出，所以它的權重也不該被大幅更動。

---

### Part 3 / 4 / 5：C 語言實作（完整程式碼）

> [!important] 程式碼保留原則
> 以下完整收錄原文所有 C 程式碼片段，**未省略、未以註解取代**。程式碼內容保持英文原文。各區塊對應原文的 3.1～4.2 小節，最後附 Part 5 的單檔完整版。

#### 3.1 設定：標頭檔與常數

```c
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

#define INPUT_SIZE 3
#define HIDDEN_SIZE 4
#define OUTPUT_SIZE 1
#define LEARNING_RATE 0.0001
#define EPOCHS 1000
```

**為什麼是這些值？** `INPUT_SIZE 3`（房間數、坪數、距離）、`HIDDEN_SIZE 4`（夠學模式又不過多）、`OUTPUT_SIZE 1`（預測一個房價）、`LEARNING_RATE 0.0001`（小步穩定學習）、`EPOCHS 1000`（資料跑 1000 遍）。

#### 3.2 網路結構（The Network Structure）

```c
typedef struct {
// Layer 1: Input to Hidden
double weights_ih[HIDDEN_SIZE][INPUT_SIZE]; // 4×3 matrix
double bias_h[HIDDEN_SIZE]; // 4 biases

// Layer 2: Hidden to Output
double weights_ho[OUTPUT_SIZE][HIDDEN_SIZE]; // 1×4 matrix
double bias_o[OUTPUT_SIZE]; // 1 bias

// Activations (saved for backprop)
double hidden[HIDDEN_SIZE]; // After ReLU
double output[OUTPUT_SIZE]; // Final output

// Pre-activations (needed for gradients)
double z_hidden[HIDDEN_SIZE]; // Before ReLU
double z_output[OUTPUT_SIZE]; // Before output
} NeuralNetwork;
```

**為什麼要存 z 值？** 反向傳播計算 ReLU 導數時需要它們。

#### 3.3 激活函數

```c
// ReLU: max(0, x)
double relu(double x) {
return (x > 0) ? x : 0;
}

// ReLU derivative: 1 if x>0, else 0
double relu_derivative(double x) {
return (x > 0) ? 1.0 : 0.0;
}
```

#### 3.4 權重初始化

```c
void init_network(NeuralNetwork *nn) {
srand(time(NULL));

// Initialize input → hidden
for (int i = 0; i < HIDDEN_SIZE; i++) {
for (int j = 0; j < INPUT_SIZE; j++) {
// Random between -0.5 and 0.5
nn->weights_ih[i][j] = ((double)rand() / RAND_MAX) - 0.5;
}
nn->bias_h[i] = ((double)rand() / RAND_MAX) - 0.5;
}

// Initialize hidden → output
for (int i = 0; i < OUTPUT_SIZE; i++) {
for (int j = 0; j < HIDDEN_SIZE; j++) {
nn->weights_ho[i][j] = ((double)rand() / RAND_MAX) - 0.5;
}
nn->bias_o[i] = ((double)rand() / RAND_MAX) - 0.5;
}
}
```

**為什麼隨機？** 若所有權重相同，所有神經元會學到同樣的模式；隨機初始化打破這種對稱性（symmetry）。**為什麼 -0.5 到 0.5？** 小值避免激活值爆炸，又不至於小到學習停滯。

#### 3.5 前向傳播

```c
void forward_propagation(NeuralNetwork *nn, double input[INPUT_SIZE]) {
// LAYER 1: Input → Hidden
for (int i = 0; i < HIDDEN_SIZE; i++) {
// Weighted sum: z = w·x + b
nn->z_hidden[i] = nn->bias_h[i];
for (int j = 0; j < INPUT_SIZE; j++) {
nn->z_hidden[i] += nn->weights_ih[i][j] * input[j];
}
// Activation: a = ReLU(z)
nn->hidden[i] = relu(nn->z_hidden[i]);
}

// LAYER 2: Hidden → Output
for (int i = 0; i < OUTPUT_SIZE; i++) {
// Weighted sum
nn->z_output[i] = nn->bias_o[i];
for (int j = 0; j < HIDDEN_SIZE; j++) {
nn->z_output[i] += nn->weights_ho[i][j] * nn->hidden[j];
}
// Linear activation (no function)
nn->output[i] = nn->z_output[i];
}
}
```

#### 3.6 反向傳播（學習發生的地方）

```c
void backward_propagation(NeuralNetwork *nn, double input[INPUT_SIZE],
double target[OUTPUT_SIZE]) {

// STEP 1: Calculate output layer error
// For MSE: error = predicted - actual
double output_error[OUTPUT_SIZE];
for (int i = 0; i < OUTPUT_SIZE; i++) {
output_error[i] = nn->output[i] - target[i];
}

// STEP 2: Backpropagate to hidden layer
// hidden_error = output_error × weight × ReLU'(z)
double hidden_error[HIDDEN_SIZE];
for (int i = 0; i < HIDDEN_SIZE; i++) {
hidden_error[i] = 0.0;
// Sum weighted errors from next layer
for (int j = 0; j < OUTPUT_SIZE; j++) {
hidden_error[i] += output_error[j] * nn->weights_ho[j][i];
}
// Multiply by ReLU derivative
hidden_error[i] *= relu_derivative(nn->z_hidden[i]);
}

// STEP 3: Update hidden → output weights
for (int i = 0; i < OUTPUT_SIZE; i++) {
for (int j = 0; j < HIDDEN_SIZE; j++) {
// gradient = error × previous_activation
nn->weights_ho[i][j] -= LEARNING_RATE * output_error[i] * nn->hidden[j];
}
nn->bias_o[i] -= LEARNING_RATE * output_error[i];
}

// STEP 4: Update input → hidden weights
for (int i = 0; i < HIDDEN_SIZE; i++) {
for (int j = 0; j < INPUT_SIZE; j++) {
nn->weights_ih[i][j] -= LEARNING_RATE * hidden_error[i] * input[j];
}
nn->bias_h[i] -= LEARNING_RATE * hidden_error[i];
}
}
```

#### 3.7 資料正規化

```c
void normalize_data(double data[][INPUT_SIZE], int num_samples,
double min[INPUT_SIZE], double max[INPUT_SIZE]) {
// Find min and max for each feature
for (int j = 0; j < INPUT_SIZE; j++) {
min[j] = data[0][j];
max[j] = data[0][j];
for (int i = 1; i < num_samples; i++) {
if (data[i][j] < min[j]) min[j] = data[i][j];
if (data[i][j] > max[j]) max[j] = data[i][j];
}
}

// Normalize: (value - min) / (max - min)
for (int i = 0; i < num_samples; i++) {
for (int j = 0; j < INPUT_SIZE; j++) {
data[i][j] = (data[i][j] - min[j]) / (max[j] - min[j]);
}
}
}
```

#### 4.1 訓練迴圈（The Training Loop）

```c
void train(NeuralNetwork *nn, double inputs[][INPUT_SIZE],
double targets[][OUTPUT_SIZE], int num_samples) {

for (int epoch = 0; epoch < EPOCHS; epoch++) {
double total_loss = 0.0;

// Train on each example
for (int i = 0; i < num_samples; i++) {
// Forward pass: make prediction
forward_propagation(nn, inputs[i]);

// Calculate loss (MSE)
for (int j = 0; j < OUTPUT_SIZE; j++) {
double error = nn->output[j] - targets[i][j];
total_loss += error * error;
}

// Backward pass: update weights
backward_propagation(nn, inputs[i], targets[i]);
}

// Average loss over all samples
total_loss /= num_samples;

// Print progress
if (epoch % 100 == 0) {
printf("Epoch %d, Loss: %.4f\n", epoch, total_loss);
}
}
}
```

#### Part 5：完整可編譯程式（Complete Working Code）

```c
// neural_network.c - Complete Implementation
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

#define INPUT_SIZE 3
#define HIDDEN_SIZE 4
#define OUTPUT_SIZE 1
#define LEARNING_RATE 0.0001
#define EPOCHS 1000

typedef struct {
double weights_ih[HIDDEN_SIZE][INPUT_SIZE];
double bias_h[HIDDEN_SIZE];
double weights_ho[OUTPUT_SIZE][HIDDEN_SIZE];
double bias_o[OUTPUT_SIZE];
double hidden[HIDDEN_SIZE];
double output[OUTPUT_SIZE];
double z_hidden[HIDDEN_SIZE];
double z_output[OUTPUT_SIZE];
} NeuralNetwork;

double relu(double x) {
return (x > 0) ? x : 0;
}

double relu_derivative(double x) {
return (x > 0) ? 1.0 : 0.0;
}

void init_network(NeuralNetwork *nn) {
srand(time(NULL));
for (int i = 0; i < HIDDEN_SIZE; i++) {
for (int j = 0; j < INPUT_SIZE; j++) {
nn->weights_ih[i][j] = ((double)rand() / RAND_MAX) - 0.5;
}
nn->bias_h[i] = ((double)rand() / RAND_MAX) - 0.5;
}
for (int i = 0; i < OUTPUT_SIZE; i++) {
for (int j = 0; j < HIDDEN_SIZE; j++) {
nn->weights_ho[i][j] = ((double)rand() / RAND_MAX) - 0.5;
}
nn->bias_o[i] = ((double)rand() / RAND_MAX) - 0.5;
}
}

void forward_propagation(NeuralNetwork *nn, double input[INPUT_SIZE]) {
for (int i = 0; i < HIDDEN_SIZE; i++) {
nn->z_hidden[i] = nn->bias_h[i];
for (int j = 0; j < INPUT_SIZE; j++) {
nn->z_hidden[i] += nn->weights_ih[i][j] * input[j];
}
nn->hidden[i] = relu(nn->z_hidden[i]);
}
for (int i = 0; i < OUTPUT_SIZE; i++) {
nn->z_output[i] = nn->bias_o[i];
for (int j = 0; j < HIDDEN_SIZE; j++) {
nn->z_output[i] += nn->weights_ho[i][j] * nn->hidden[j];
}
nn->output[i] = nn->z_output[i];
}
}

void backward_propagation(NeuralNetwork *nn, double input[INPUT_SIZE],
double target[OUTPUT_SIZE]) {
double output_error[OUTPUT_SIZE];
for (int i = 0; i < OUTPUT_SIZE; i++) {
output_error[i] = nn->output[i] - target[i];
}

double hidden_error[HIDDEN_SIZE];
for (int i = 0; i < HIDDEN_SIZE; i++) {
hidden_error[i] = 0.0;
for (int j = 0; j < OUTPUT_SIZE; j++) {
hidden_error[i] += output_error[j] * nn->weights_ho[j][i];
}
hidden_error[i] *= relu_derivative(nn->z_hidden[i]);
}

for (int i = 0; i < OUTPUT_SIZE; i++) {
for (int j = 0; j < HIDDEN_SIZE; j++) {
nn->weights_ho[i][j] -= LEARNING_RATE * output_error[i] * nn->hidden[j];
}
nn->bias_o[i] -= LEARNING_RATE * output_error[i];
}

for (int i = 0; i < HIDDEN_SIZE; i++) {
for (int j = 0; j < INPUT_SIZE; j++) {
nn->weights_ih[i][j] -= LEARNING_RATE * hidden_error[i] * input[j];
}
nn->bias_h[i] -= LEARNING_RATE * hidden_error[i];
}
}

void normalize_data(double data[][INPUT_SIZE], int num_samples,
double min[INPUT_SIZE], double max[INPUT_SIZE]) {
for (int j = 0; j < INPUT_SIZE; j++) {
min[j] = data[0][j];
max[j] = data[0][j];
for (int i = 1; i < num_samples; i++) {
if (data[i][j] < min[j]) min[j] = data[i][j];
if (data[i][j] > max[j]) max[j] = data[i][j];
}
}
for (int i = 0; i < num_samples; i++) {
for (int j = 0; j < INPUT_SIZE; j++) {
data[i][j] = (data[i][j] - min[j]) / (max[j] - min[j]);
}
}
}

void train(NeuralNetwork *nn, double inputs[][INPUT_SIZE],
double targets[][OUTPUT_SIZE], int num_samples) {
for (int epoch = 0; epoch < EPOCHS; epoch++) {
double total_loss = 0.0;
for (int i = 0; i < num_samples; i++) {
forward_propagation(nn, inputs[i]);
for (int j = 0; j < OUTPUT_SIZE; j++) {
double error = nn->output[j] - targets[i][j];
total_loss += error * error;
}
backward_propagation(nn, inputs[i], targets[i]);
}
total_loss /= num_samples;
if (epoch % 100 == 0) {
printf("Epoch %d, Loss: %.4f\n", epoch, total_loss);
}
}
}

int main() {
double training_inputs[][INPUT_SIZE] = {
{3, 1500, 2.0}, {4, 2000, 1.5}, {2, 1000, 3.0}, {5, 2500, 1.0},
{3, 1800, 2.5}, {4, 2200, 1.2}, {2, 900, 4.0}, {6, 3000, 0.8}
};
double training_targets[][OUTPUT_SIZE] = {
{300}, {400}, {200}, {500}, {350}, {450}, {180}, {600}
};
int num_samples = 8;

double min[INPUT_SIZE], max[INPUT_SIZE];
normalize_data(training_inputs, num_samples, min, max);

double target_min = training_targets[0][0];
double target_max = training_targets[0][0];
for (int i = 1; i < num_samples; i++) {
if (training_targets[i][0] < target_min) target_min = training_targets[i][0];
if (training_targets[i][0] > target_max) target_max = training_targets[i][0];
}
for (int i = 0; i < num_samples; i++) {
training_targets[i][0] = (training_targets[i][0] - target_min) /
(target_max - target_min);
}

NeuralNetwork nn;
init_network(&nn);

printf("Training Neural Network for House Price Prediction\n");
printf("Architecture: %d → %d → %d\n\n", INPUT_SIZE, HIDDEN_SIZE, OUTPUT_SIZE);

train(&nn, training_inputs, training_targets, num_samples);

printf("\n=== Testing Predictions ===\n");
for (int i = 0; i < num_samples; i++) {
forward_propagation(&nn, training_inputs[i]);
double predicted = nn.output[0] * (target_max - target_min) + target_min;
double actual = training_targets[i][0] * (target_max - target_min) + target_min;
printf("Sample %d: Predicted $%.2fk, Actual $%.2fk\n", i+1, predicted, actual);
}

printf("\n=== New Prediction ===\n");
double new_house[INPUT_SIZE] = {3, 1600, 1.8};
for (int j = 0; j < INPUT_SIZE; j++) {
new_house[j] = (new_house[j] - min[j]) / (max[j] - min[j]);
}
forward_propagation(&nn, new_house);
double prediction = nn.output[0] * (target_max - target_min) + target_min;
printf("House: 3 rooms, 1600 sqft, 1.8km from market\n");
printf("Predicted price: $%.2fk\n", prediction);

return 0;
}
```

編譯與執行：

```bash
gcc -o nn neural_network.c -lm
./nn
```

---

## 程式架構分析（用 ccq 解析）

> [!info] 分析方法
> 以下圖表並非憑空繪製，而是把完整原始碼存成 `neural_network.c` 後，用 **ccq（clangd 驅動）** 實際查詢 `callers` / `callees` 得到的**真實函式呼叫圖**。指令範例：`ccq callees main`、`ccq callers forward_propagation`。

### 函式呼叫圖（Call Graph）

ccq 解析出的函式相依關係如下（`f → g` 表示 f 呼叫 g）：

```
                         ┌──────────┐
                         │  main()  │  程式進入點（entry point）
                         └────┬─────┘
        ┌────────────┬────────┼─────────────┬──────────────┐
        ▼            ▼        ▼             ▼              ▼
┌──────────────┐ ┌────────────┐ ┌─────────┐ ┌────────────────────┐ ┌────────┐
│init_network()│ │normalize_  │ │ train() │ │forward_propagation │ │ printf │
│              │ │  data()    │ │         │ │  （測試/新預測）    │ │ (libc) │
└──────┬───────┘ └────────────┘ └────┬────┘ └─────────┬──────────┘ └────────┘
       │            (leaf)           │                │
   ┌───┴────┐               ┌────────┴─────────┐      ▼
   ▼   ▼    ▼               ▼                  ▼   ┌──────┐
 srand rand time   forward_propagation  backward_  │relu()│
 (libc)(libc)(libc)        │            propagation └──────┘
                           ▼                  │
                       ┌──────┐               ▼
                       │relu()│        ┌────────────────┐
                       └──────┘        │relu_derivative │
                                       └────────────────┘
```

> [!note] ccq 驗證到的關鍵關係
> - `main` 的 callees：`init_network`、`normalize_data`、`train`、`forward_propagation`、`printf`
> - `train` 的 callees：`forward_propagation`、`backward_propagation`、`printf`
> - `forward_propagation` → `relu`（唯一呼叫者：`main`、`train`）
> - `backward_propagation` → `relu_derivative`（唯一呼叫者：`train`）
> - `init_network` → `srand`、`rand`、`time`
> - `normalize_data`：葉節點（leaf，不呼叫任何專案函式）

**設計觀察**：`forward_propagation` 被 `train`（訓練時）與 `main`（測試/新預測時）共用，是整個系統的核心熱點（hotspot）。學習邏輯則完全集中在 `train` → `backward_propagation` 這條鏈上。

### 資料流與層級對應（Data Flow）

```
原始資料 (rooms, area, distance) + 房價
        │
        ▼  normalize_data()  →  把特徵與目標壓到 [0,1]
[正規化輸入] ──────────────────────────────┐
        │                                  │
        ▼  init_network()  →  隨機權重      │
        │  (weights_ih, bias_h,            │
        │   weights_ho, bias_o)            │
        ▼                                  │
   ┌─────────────── train() 迴圈 ×EPOCHS ──┴───────────┐
   │   for each sample:                                │
   │     forward_propagation()  →  z_hidden→ReLU→hidden│
   │                               →z_output→output    │
   │     累加 MSE loss                                  │
   │     backward_propagation() →  更新所有權重/偏差     │
   └───────────────────────────────────────────────────┘
        │
        ▼  forward_propagation()（推論）+ 反正規化（denormalize）
   預測房價 ($k)
```

### 一次訓練迭代的時序圖（Sequence Diagram）

```
 train()        forward_prop      relu        backward_prop   relu_derivative
   │                 │             │                │               │
   │──①前向────────►│             │                │               │
   │                 │──ReLU──────►│                │               │
   │                 │◄────────────│                │               │
   │◄──output────────│             │                │               │
   │                                                                 │
   │── 累加 (output-target)² 到 total_loss ──┐                       │
   │◄───────────────────────────────────────┘                       │
   │                                                                 │
   │──②反向──────────────────────────────────►│                     │
   │                                          │──ReLU'(z_hidden)────►│
   │                                          │◄────────────────────│
   │   weights_ho/bias_o、weights_ih/bias_h 全部 -= lr×grad           │
   │◄─────────────────────────────────────────                       │
```

---

## 架構師觀點（Architect's View）

### ✅ 優點（Strengths）

| 面向 | 評估 | 說明 |
|------|------|------|
| 可讀性（Readability） | ⭐⭐⭐⭐⭐ | 函式單一職責、命名直白，前向/反向/正規化各自獨立 |
| 教學價值（Pedagogy） | ⭐⭐⭐⭐⭐ | 每段先講 why 再給 code，數值推導完整 |
| 零依賴（Zero Dependency） | ⭐⭐⭐⭐⭐ | 僅用標準函式庫 + `-lm`，任何環境都能編 |
| 正確性（Correctness） | ⭐⭐⭐⭐ | 前向/反向傳播數學正確；但超參數未調好（見下） |
| 可擴展性（Scalability） | ⭐⭐ | 層數與尺寸用 `#define` 寫死，無法動態加層 |

> [!tip] 值得學習的設計
> 把**前激活值 `z_hidden` / `z_output` 存進 struct**，讓反向傳播能直接取用做 ReLU 導數——這是「forward 為 backward 預留中間狀態」的經典手法，也是現代框架 autograd 的雛形。

### ⚠️ 缺點與風險（Weaknesses & Risks）

> [!warning] 實測揭露：以原文超參數，模型學得很差
> 我實際 `gcc` 編譯執行，loss 從 0.195 跑完 1000 epochs 只降到 **0.096**，且測試預測幾乎都擠在 $306k–$358k（不論輸入），與實際 $180k–$600k 嚴重不符。**原文宣稱 Epoch 900 Loss 可達 0.0012、預測「Very good」，但這與真實執行結果不符。**

- **學習率過小（`0.0001`）**：對只有 8 筆、已正規化到 [0,1] 的資料，步伐太小，1000 epochs 遠遠不夠收斂。影響：**模型實質上沒學會**。
- **資料量過少（8 筆）+ 無 train/test 切分**：全部資料都拿來訓練，無法評估泛化（generalization）；數值「看起來像在學」但其實是欠擬合（underfitting）。
- **`-lm` 連結但其實沒用到 `math.h`**：`relu` 自己用三元運算子實作，`<math.h>` 與 `-lm` 是多餘的。
- **超參數寫死於 `#define`**：要改層數、神經元數需改原始碼重編，無法實驗。
- **未保護除以零**：`normalize_data` 若某特徵 `max == min` 會產生 `NaN`。

### 🔮 改進建議（Improvement Suggestions）

1. 把 `LEARNING_RATE` 提高到 `0.01`～`0.1` 並增加 `EPOCHS`，或改用 mini-batch；先讓 loss 真正降下來再談其他。
2. 加入 train/validation 切分與隨機打散（shuffle），避免欠擬合與假象收斂。
3. 用陣列/指標泛化層結構（取代 `#define`），支援任意層數與神經元數。
4. `normalize_data` 對 `max==min` 做保護（除數為 0 時設為 1）。

## 效能基準（Benchmark）

> [!info] 資料來源
> 以下為本筆記在本機（macOS, gcc, `-lm`）實際編譯執行的輸出，非原文宣稱值。

| 場景 | 原文宣稱 | 實測（本機單次） |
|------|---------|----------------|
| Epoch 0 Loss | 0.1234 | 0.1953 |
| Epoch 900 Loss | 0.0012（"Very good!"） | **0.0964（幾乎沒降）** |
| Sample 8 預測（實際 $600k） | —（未列） | $358.41k（嚴重偏低） |
| 新房預測（3 房/1600/1.8km） | —（未列） | $317.81k |

結論：此程式的**價值在教學（讀懂數學與程式骨架），而非作為堪用的預測器**。效能瓶頸不在速度（8 筆資料瞬間跑完），而在**超參數設定導致的學習品質**。

## 快速上手（Quick Start）

```bash
# 1. 將 Part 5 完整程式存成 neural_network.c
# 2. 編譯（-lm 連結數學庫；本例其實非必要）
gcc -o nn neural_network.c -lm
# 3. 執行
./nn
# 建議：把 LEARNING_RATE 改成 0.05、EPOCHS 改成 5000 再跑一次，觀察 loss 是否真的下降
```

## 我的心得（My Takeaways）

- 這份程式碼最大的價值是把「神經網路」從黑盒子拆成**8 個一眼看懂的 C 函式**——`forward_propagation`、`backward_propagation`、`relu` 三者就是整個深度學習的縮影。
- **「能跑」不等於「學會了」**：原文的訓練輸出看似在進步，但實測證明超參數沒調好時，模型只是在原地小幅擺動。這提醒我——讀技術文章要動手驗證，不能只信作者貼的數字（呼應記憶中「引用工具輸出前要實際看到」的教訓）。
- 用 **ccq 對教學程式碼畫呼叫圖**意外好用：即使是單檔小程式，先看 call graph 再讀碼，能快速分辨「核心熱點（forward_propagation）」與「一次性流程（init/normalize）」。

## 待補充（Open Questions）

- 原文 Epoch 900 Loss 0.0012 是怎麼得到的？是否用了與貼出程式不同的超參數，或挑選了特別好的隨機種子？（搜尋關鍵字：`neural network underfitting learning rate too small`）
- 把 `LEARNING_RATE` 調大、`EPOCHS` 增多後，這個 `3→4→1` 結構對 8 筆資料的理論最低 loss 是多少？會不會因資料太少而無法有意義地學習？
- 為什麼輸出層完全不用激活函數，在「房價恆為正」的情境下不會造成問題？若改用 ReLU 輸出會更好還是更差？（搜尋：`linear output layer regression activation`）
- 原文提到的「next steps」之一 sigmoid/tanh，套到這個房價迴歸任務上，會比 ReLU 表現好嗎？（搜尋：`sigmoid vs relu regression from scratch`）
- 這種「純 C、無矩陣庫」的寫法，擴展到多層、上萬參數時，效能與可維護性會在哪裡先崩潰？（搜尋：`naive C neural network vs BLAS performance`）

---

## 知識層次分析（Bloom's Taxonomy Analysis）

> 以下從五個認知層次對本篇內容進行結構化分析，協助從記憶到評估逐層深化理解。

| 認知層次 | 核心目的 | 對本文的具體應用 |
|---------|---------|--------------|
| **記憶（被動）** | 確認資訊存在，單純資訊檢索 | 核心術語：神經元（neuron）、ReLU、前向傳播（forward propagation）、反向傳播（backward propagation）、MSE 損失、梯度下降（gradient descent）、正規化（normalization）；核心 API：`forward_propagation` / `backward_propagation` / `relu` / `init_network`；關鍵常數：`LEARNING_RATE 0.0001`、`EPOCHS 1000`、結構 `3→4→1` |
| **理解（半被動）** | 解釋概念含義及關聯 | 一個神經元 = 加權總和 + 激活；多個神經元 = 一層；前向傳播算預測、損失衡量錯誤、反向傳播用鏈鎖法則回傳誤差並更新權重——四者構成一個訓練迴圈。ReLU 提供非線性，正規化讓不同尺度特徵公平競爭 |
| **分析（主動）** | 檢驗論點、找出假設 | 關鍵假設：「loss 下降 = 模型學會了」。實測推翻——loss 從 0.195 只降到 0.096，預測全擠在 $306k–$358k。隱含前提：原文宣稱的 0.0012 可能來自不同超參數或未公開的設定，未被原文挑明 |
| **應用（主動）** | 將知識套用情境、轉為行動 | ① 把 Part 5 程式存檔、`gcc -o nn neural_network.c -lm` 跑一次，親眼看 loss 曲線；② 改 `LEARNING_RATE=0.05`、`EPOCHS=5000` 重跑，驗證收斂是否改善；③ 用 ccq 對任何小型 C 程式畫 call graph 來輔助閱讀 |
| **評估（主動）** | 判斷方案優劣與權衡 | 純 C 手刻 vs 用 PyTorch/NumPy：手刻贏在「徹底理解 + 零依賴 + 可嵌入式部署」，輸在「開發效率、數值穩定性、可擴展性」。作為**學習教材**極佳；作為**生產預測器**不堪用。學會原理後，真實專案仍應改用成熟框架 |

### 分析型追問（Socratic Follow-up）

- **澄清**：「學習（learning）」在本文的精確定義是什麼？是「loss 下降」還是「測試集預測接近真值」？兩者在本例出現了分歧。
- **假設**：本文成立的最關鍵前提是「1000 epochs 足以讓 `lr=0.0001` 收斂」。若此前提不成立（實測證明不成立），那「神經網路能學會房價」的結論在這份程式碼裡其實沒被證明。
- **證據**：原文「Epoch 900 Loss: 0.0012、預測 Very good」缺乏可重現的證據；如何補強？→ 公開隨機種子、附上完整測試輸出、固定超參數。
- **觀點**：若站在「這只是教學示範」的立場，超參數沒調好無傷大雅；但若站在「初學者會照抄並以為自己訓練成功」的立場，這是會誤導人的缺陷。
- **後果**：若初學者照本文「next steps」一路加層、換激活函數，卻從未修正過小的學習率，12 個月後他可能堆出更複雜卻同樣學不動的網路，並錯誤歸因於「資料不夠」而非超參數。

### 方案批判三問（Critical Evaluation）

1. **最大的風險是什麼？** — 教學誤導：讀者照抄程式、看到 loss 在降就以為「訓練成功」，把一個實質欠擬合（underfitting）的模型當成可用，並內化錯誤的超參數直覺。損失不是系統停擺，而是**錯誤的學習與認知**。
2. **什麼情況下會失敗？** — ①學習率太小 + epochs 不足（本例正是如此）；②資料量太少又無 train/test 切分，無法察覺欠擬合；③某特徵 `max==min` 時正規化除以零產生 `NaN`；④把它當真實預測器用於 8 筆以外的分佈。
3. **有沒有更好的替代方案？** — 學原理：Karpathy 的 micrograd / makemore（Python，附完整講解與可重現結果）更嚴謹；要實用：直接用 PyTorch/scikit-learn，幾行就能得到調好且穩定的迴歸模型。**何時仍選純 C？** 嵌入式/無 runtime 環境、或刻意要「徹底看穿每一行數學」時。

## 相關連結（Related）

- [[2026-04-12-HARNESS-ENGINEERING-HUNGYI-LEE-NTU-LLM-GUIDANCE]] — 同屬「機器學習導論」教學脈絡，可對照 LLM 時代與最底層數學兩種理解路徑
- [[2025-10-16-DESIGN-YOUR-SOCRATIC-AI-MENTOR-FRAMEWORK]] — 本文「先懂 why 再講 how」與蘇格拉底式「理解優先、雙向思辨」教學法高度呼應
- [[2026-04-29-ANDREJ-KARPATHY-FROM-VIBE-CODING-TO-AGENTIC-ENGINEERING-SOFTWARE-3-0]] — Karpathy「可外包思考，無法外包理解」正是本文「從最深層理解神經網路」的價值主張

## References
- [原文（X Article）](https://x.com/TheVixhal/status/2019831123682181418)
- [作者 vixhaℓ（@TheVixhal）](https://x.com/TheVixhal) — Double Major in Physics and AI/ML (Minor in Math)
