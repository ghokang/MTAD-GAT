import numpy as np
from sklearn.metrics import f1_score

from utils.adjustpred import adjust_predicts
from utils.spot import SPOT


def pot_threshold(train_score, test_score, q=1e-3, level=0.98, dynamic=False):
    s = SPOT(q)
    s.fit(train_score, test_score)
    s.initialize(level=level, min_extrema=False)  # Calibration step
    ret = s.run(dynamic=dynamic, with_alarm=False)

    best_threshold = np.mean(ret["thresholds"])
    return best_threshold


def bestf1_threshold(test_scores, test_label, start=0.01, end=2, search_step=100):
    best_f1 = 0.0
    best_threshold = 0.0

    for i in range(search_step):
        threshold = start + i * ((end - start) / search_step)
        test_pred = (test_scores > threshold).astype(np.int64)
        test_pred = adjust_predicts(test_label, test_pred)
        f1 = f1_score(test_label, test_pred)

        if f1 > best_f1:
            best_threshold = threshold
            best_f1 = f1

    return best_threshold


def epsilon_threshold(train_scores, reg_level=1):
    e_s = train_scores
    best_threshold = None
    max_score = -10000000
    mean_e_s = np.mean(e_s) ## train score의 평균 및 표준편차
    sd_e_s = np.std(e_s)

    for z in np.arange(2.5, 12, 0.5):
        epsilon = mean_e_s + sd_e_s * z ## 정상,비정상 판단
        pruned_e_s = e_s[e_s < epsilon] ## e_s 값이 epsilon 값보다 작은 값들 ## 정상 객체

        i_anom = np.argwhere(e_s >= epsilon).reshape(-1, ) ## e_s 값이 espilon 값보다 큰 경우 ## 비정상 객체의 위치
        buffer = np.arange(1, 50) ## 주변 데이터 포인트 사이의 잠재적인 상관관계나 종속성 포착
        #### "smoothed errors"
        i_anom = np.sort(
            np.concatenate(
                (
                    i_anom,
                    np.array([i + buffer for i in i_anom]).flatten(),
                    np.array([i - buffer for i in i_anom]).flatten(),
                )
            )
        )
        i_anom = i_anom[(i_anom < len(e_s)) & (i_anom >= 0)] ## 인덱스 범위가 0보다 작거나 e_s의 길이보다 큰 경우 인덱스 제거
        i_anom = np.sort(np.unique(i_anom)) ## 최종적인 i_anom에는 데이터셋 내의 모든 비정상적인 인스턴스의 인덱스와 인근 데이터 포인트가 포함
        
        if len(i_anom) > 0:
            mean_perc_decrease = (mean_e_s - np.mean(pruned_e_s)) / mean_e_s
            sd_perc_decrease = (sd_e_s - np.std(pruned_e_s)) / sd_e_s
            denom = None
            if reg_level == 0:
                denom = 1
            elif reg_level == 1:
                denom = len(i_anom)
            elif reg_level == 2:
                denom = len(i_anom) ** 2
                
                # denom => penalty term
            score = (mean_perc_decrease + sd_perc_decrease) / denom

            if score >= max_score and len(i_anom) < (len(e_s) * 0.5):
                max_score = score
                best_threshold = epsilon

    if best_threshold is None:
        best_threshold = np.max(e_s)
    return best_threshold
