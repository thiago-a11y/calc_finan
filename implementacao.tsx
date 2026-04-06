Aqui está uma implementação básica da calculadora de financiamento imobiliário web utilizando React, TypeScript e CSS para o frontend, e Node.js e MongoDB para o backend.

**Frontend (React, TypeScript, CSS)**

Crie um novo projeto React utilizando o comando `npx create-react-app calculadora-financiamento-imobiliario --template typescript`.

Adicione os seguintes arquivos e códigos:

**components/Calculadora.tsx**
```typescript
import React, { useState } from 'react';

interface CalculadoraProps {
  valorImovel: number;
  prazoFinanciamento: number;
  taxaJuros: number;
}

const Calculadora: React.FC<CalculadoraProps> = ({
  valorImovel,
  prazoFinanciamento,
  taxaJuros,
}) => {
  const [valorEntrada, setValorEntrada] = useState(0);
  const [valorFinanciamento, setValorFinanciamento] = useState(0);
  const [parcelas, setParcelas] = useState(0);

  const calcularFinanciamento = () => {
    const valorFinanciamentoCalculado = valorImovel - valorEntrada;
    const parcelasCalculadas = Math.round(
      valorFinanciamentoCalculado / (prazoFinanciamento * 12)
    );
    setValorFinanciamento(valorFinanciamentoCalculado);
    setParcelas(parcelasCalculadas);
  };

  return (
    <div>
      <h1>Calculadora de Financiamento Imobiliário</h1>
      <form>
        <label>
          Valor do Imóvel:
          <input
            type="number"
            value={valorImovel}
            onChange={(e) => setValorImovel(Number(e.target.value))}
          />
        </label>
        <label>
          Prazo de Financiamento (anos):
          <input
            type="number"
            value={prazoFinanciamento}
            onChange={(e) => setPrazoFinanciamento(Number(e.target.value))}
          />
        </label>
        <label>
          Taxa de Juros (%):
          <input
            type="number"
            value={taxaJuros}
            onChange={(e) => setTaxaJuros(Number(e.target.value))}
          />
        </label>
        <label>
          Valor de Entrada:
          <input
            type="number"
            value={valorEntrada}
            onChange={(e) => setValorEntrada(Number(e.target.value))}
          />
        </label>
        <button type="button" onClick={calcularFinanciamento}>
          Calcular Financiamento
        </button>
      </form>
      <p>
        Valor do Financiamento: R${valorFinanciamento.toFixed(2)}
      </p>
      <p>
        Número de Parcelas: {parcelas}
      </p>
    </div>
  );
};

export default Calculadora;
```

**App.tsx**
```typescript
import React from 'react';
import Calculadora from './components/Calculadora';

const App: React.FC = () => {
  return (
    <div>
      <Calculadora valorImovel={100000} prazoFinanciamento={10} taxaJuros={8} />
    </div>
  );
};

export default App;
```

**Backend (Node.js, MongoDB)**

Crie um novo projeto Node.js e instale as dependências necessárias:

```bash
npm init -y
npm install express mongoose
```

Crie os seguintes arquivos e códigos:

**models/Financiamento.ts**
``