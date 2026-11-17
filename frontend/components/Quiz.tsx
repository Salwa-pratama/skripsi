"use client";

import { useState } from "react";
import type { QuizQuestion } from "@/lib/types";
import { CheckIcon, LightbulbIcon, ResetIcon } from "./icons";

export function Quiz({ questions }: { questions: QuizQuestion[] }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState(false);

  if (!questions.length) return null;

  const answeredCount = Object.keys(answers).length;
  const score = questions.reduce(
    (total, question, index) => total + (answers[index] === question.answer ? 1 : 0),
    0,
  );

  function reset() {
    setAnswers({});
    setSubmitted(false);
  }

  return (
    <section className="quiz-card" id="kuis-evaluasi" aria-labelledby="quiz-title">
      <div className="quiz-head">
        <div>
          <p className="section-kicker">Evaluasi Pemahaman 25 Menit</p>
          <h2 id="quiz-title">Kuis Evaluasi Pasca-Sesi</h2>
        </div>
        <span className="quiz-counter">
          {answeredCount}/{questions.length} terjawab
        </span>
      </div>

      <div className="quiz-list">
        {questions.map((question, questionIndex) => (
          <fieldset className="quiz-question" key={questionIndex}>
            <legend>
              <span className="quiz-number">{String(questionIndex + 1).padStart(2, "0")}</span>
              <span className="quiz-question-text">{question.question}</span>
            </legend>
            <div className="quiz-options">
              {question.options.map((option, optionIndex) => {
                const selected = answers[questionIndex] === optionIndex;
                const isCorrect = question.answer === optionIndex;
                const state = submitted
                  ? isCorrect
                    ? "is-correct"
                    : selected
                      ? "is-wrong"
                      : ""
                  : selected
                    ? "is-selected"
                    : "";
                return (
                  <label className={`quiz-option ${state}`} key={optionIndex}>
                    <input
                      type="radio"
                      name={`question-${questionIndex}`}
                      checked={selected}
                      disabled={submitted}
                      onChange={() =>
                        setAnswers((previous) => ({
                          ...previous,
                          [questionIndex]: optionIndex,
                        }))
                      }
                    />
                    <span className="quiz-radio" aria-hidden="true" />
                    <span>{option}</span>
                    {submitted && isCorrect && <CheckIcon size={16} className="quiz-check" />}
                  </label>
                );
              })}
            </div>
            {submitted && (
              <p className="quiz-explanation">
                <LightbulbIcon size={16} />
                <span>{question.explanation}</span>
              </p>
            )}
          </fieldset>
        ))}
      </div>

      <div className="quiz-footer">
        {submitted ? (
          <>
            <p className="quiz-score" aria-live="polite">
              Skor kamu <strong>{score}</strong> dari {questions.length}.
              {score === questions.length
                ? " Semua benar, lanjut ke bab berikutnya!"
                : " Baca ulang bagian yang masih terasa asing, lalu coba lagi."}
            </p>
            <button type="button" className="button button-ghost button-small" onClick={reset}>
              <ResetIcon size={16} />
              Ulangi latihan
            </button>
          </>
        ) : (
          <>
            <p className="quiz-hint">
              {answeredCount === questions.length
                ? "Semua soal terjawab. Saatnya cek hasil."
                : "Jawab semua soal untuk melihat pembahasan."}
            </p>
            <button
              type="button"
              className="button button-primary button-small"
              onClick={() => setSubmitted(true)}
              disabled={answeredCount !== questions.length}
            >
              Periksa jawaban
            </button>
          </>
        )}
      </div>
    </section>
  );
}
