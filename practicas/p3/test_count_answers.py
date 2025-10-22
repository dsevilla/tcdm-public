from pandas import DataFrame, Series, notna, read_csv


def test_so_count_answers() -> None:
    """Compara so_count_answers.py con implementación pandas de referencia"""
    output_file: str = "so_count_answers.out"
    posts_file: str = "Posts.csv"

    # Usar el resultado del fichero generado previamente
    mrjob_results: DataFrame = read_csv(
        output_file, sep="\t", header=None, names=["QuestionId", "AnswerCount"]
    )

    # Implementación de referencia con pandas
    df: DataFrame = read_csv(posts_file)

    # Filtrar respuestas (PostTypeId = 2) con ParentId válido
    answers: DataFrame = df[df["PostTypeId"] == 2]

    # Contar respuestas por pregunta (ParentId ya es el índice)
    answer_counts: Series = answers["ParentId"].value_counts(sort=False)

    # Comparar resultados
    assert len(mrjob_results) == len(
        answer_counts
    ), f"Diferente número de preguntas: MRJob={len(mrjob_results)}, Pandas={len(answer_counts)}"

    for question_id, mrjob_count in mrjob_results.itertuples(index=False):
        pandas_count: int = answer_counts.get(question_id, 0)
        assert (
            mrjob_count == pandas_count
        ), f"Diferencia en pregunta {question_id}: MRJob={mrjob_count}, Pandas={pandas_count}"

    # Verificar que el campo AnswerCount de cada pregunta coincide con el conteo real
    questions: DataFrame = df[df["PostTypeId"] == 1]
    questions_with_answers: DataFrame = questions[questions["Id"].isin(answer_counts.index)]

    for _, question in questions_with_answers.iterrows():
        question_id: int = int(question["Id"])
        declared_count: int = int(question["AnswerCount"]) if notna(question["AnswerCount"]) else 0
        actual_count: int = answer_counts.get(question_id, 0)

        assert declared_count == actual_count, (
            f"El campo AnswerCount no coincide para pregunta {question_id}: "
            f"AnswerCount={declared_count}, conteo real={actual_count}"
        )

    print(f"Comparación exitosa: {len(mrjob_results)} preguntas con respuestas")
    print(f"Verificación AnswerCount: {len(questions_with_answers)} preguntas verificadas")
