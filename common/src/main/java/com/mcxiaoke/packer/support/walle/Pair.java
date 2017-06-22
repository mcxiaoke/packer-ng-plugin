/*
 * Copyright (C) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.mcxiaoke.packer.support.walle;

/**
 * Pair of two elements.
 */
final class Pair<A, B> {
    private final A f;
    private final B s;

    private Pair(final A first, final B second) {
        f = first;
        s = second;
    }

    public static <A, B> Pair<A, B> of(final A first, final B second) {
        return new Pair<A, B>(first, second);
    }

    public A getFirst() {
        return f;
    }

    public B getSecond() {
        return s;
    }

    @Override
    public boolean equals(final Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        final Pair<?, ?> pair = (Pair<?, ?>) o;

        if (f != null ? !f.equals(pair.f) : pair.f != null) return false;
        return s != null ? s.equals(pair.s) : pair.s == null;
    }

    @Override
    public int hashCode() {
        int result = f != null ? f.hashCode() : 0;
        result = 31 * result + (s != null ? s.hashCode() : 0);
        return result;
    }
}
