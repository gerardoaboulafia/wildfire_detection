'use client';

interface ModelMetric {
  model: string;
  cv_auc: number;
  test_auc: number;
  test_accuracy: number;
  test_precision: number;
  test_recall: number;
  test_f1: number;
}

interface Props {
  models: ModelMetric[];
}

const BEST_MODEL = 'RandomForest';

export default function ConfusionMatrix({ models }: Props) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-bold text-white">Model Performance Comparison</h3>
      <div className="overflow-hidden rounded-lg border border-gray-700">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-800 text-xs uppercase tracking-wider text-gray-400">
              <th className="px-3 py-2 text-left">Model</th>
              <th className="px-3 py-2 text-right">CV AUC</th>
              <th className="px-3 py-2 text-right">Test AUC</th>
              <th className="px-3 py-2 text-right">F1</th>
              <th className="px-3 py-2 text-right">Recall</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => {
              const isBest = m.model === BEST_MODEL;
              return (
                <tr
                  key={m.model}
                  className={`border-t border-gray-700 ${isBest ? 'bg-orange-900/20' : ''}`}
                >
                  <td className="px-3 py-2 font-semibold text-white">
                    {m.model}
                    {isBest && (
                      <span className="ml-1 rounded bg-orange-600 px-1 py-0.5 text-xs text-white">
                        ★
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-gray-300">
                    {m.cv_auc.toFixed(4)}
                  </td>
                  <td className={`px-3 py-2 text-right font-mono font-bold ${isBest ? 'text-orange-400' : 'text-gray-300'}`}>
                    {m.test_auc.toFixed(4)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-gray-300">
                    {m.test_f1.toFixed(4)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-gray-300">
                    {m.test_recall.toFixed(4)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        CV = 10-fold spatial GroupKFold. Test = 30% held-out spatial blocks.
      </p>
    </div>
  );
}
