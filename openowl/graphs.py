import plotly.graph_objects as go


def wrap_text(text, width=50):
    """Wrap text to specified width by inserting <br> tags.

    Args:
        text (str): Text to wrap
        width (int): Maximum width of each line

    Returns:
        str: Text with <br> tags inserted for line breaks
    """
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(" ".join(current_line))

    return "<br>".join(lines)


def create_score_scatter_plot(
    df, comment_column="comment_details", score_column="toxicity_llm_score", group_column=None
):
    """Create an interactive scatter plot of toxicity scores with connected lines for grouped items.

    Args:
        df (pd.DataFrame): DataFrame containing the toxicity data
        comment_column (str): Name of column containing comment text
        score_column (str): Name of column containing toxicity scores
        group_column (str): Name of column containing group identifiers (PR/Issue IDs)

    Returns:
        go.Figure: Plotly figure object
    """
    wrapped_comments = [wrap_text(str(text)) for text in df[comment_column]]

    fig = go.Figure()

    # If group_column is provided, add lines connecting points within each group
    if group_column and group_column in df.columns:
        for group_id in df[group_column].unique():
            group_data = df[df[group_column] == group_id]
            fig.add_trace(
                go.Scatter(
                    x=group_data["datetime"],
                    y=group_data[score_column],
                    mode="lines",
                    line=dict(
                        color="rgba(128, 128, 128, 0.2)", 
                        width=1,
                        shape='linear'
                    ),
                ),
            )

    # Add scatter points (same as before)
    fig.add_trace(
        go.Scatter(
            x=df["datetime"],
            y=df[score_column],
            mode="markers",
            marker=dict(
                size=10,
                color=df[score_column],
                colorscale=[[0, "green"], [1, "red"]],
                cmin=1,
                cmax=5,
            ),
            hovertemplate="""
            <b>Time</b>: %{x}<br>
            <b>Toxicity Score</b>: %{y}<br>
            <b>Comment</b>: %{customdata}
            <extra></extra>
            """,
            customdata=wrapped_comments,
        )
    )

    fig.update_layout(
        # title='Metrics over time',
        # xaxis_title='Time',
        yaxis_title=f"{score_column}",
        height=200,
        # width=1500,
        showlegend=False,
        margin=dict(t=30),
        hoverlabel=dict(
            bgcolor="var(--background-color, white)",
            font=dict(color="var(--text-color, black)", size=12),
            align="left",
        ),
    )

    return fig
